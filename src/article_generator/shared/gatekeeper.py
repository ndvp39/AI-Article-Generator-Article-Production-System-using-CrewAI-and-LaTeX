from __future__ import annotations

import random
import time
import uuid
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock, Semaphore
from typing import Any

from article_generator.constants import TRANSIENT_HTTP_CODES
from article_generator.shared.config import ServiceLimits
from article_generator.shared.gatekeeper_models import (
    ApiCallFailedError,
    CallRecord,
    QueueFullError,
    TokenStats,
)


class ApiGatekeeper:
    def __init__(self, limits: ServiceLimits) -> None:
        self._limits = limits
        self._lock = Lock()
        self._semaphore = Semaphore(limits.concurrent_max)
        self._minute_window: deque[float] = deque()
        self._hour_window: deque[float] = deque()
        self._token_window: deque[tuple[float, int]] = deque()
        self._inflight = 0
        self._records: list[CallRecord] = []

    def execute(
        self,
        api_call: Callable,
        *args,
        agent_name: str = "unknown",
        model: str = "unknown",
        **kwargs,
    ) -> Any:
        with self._lock:
            if self._inflight >= self._limits.max_queue_depth:
                raise QueueFullError(f"Queue at max depth ({self._limits.max_queue_depth})")
            self._inflight += 1
        try:
            with self._semaphore:
                self._wait_for_slot()
                return self._run_with_retry(api_call, args, kwargs, agent_name, model)
        finally:
            with self._lock:
                self._inflight -= 1

    def _wait_for_slot(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._minute_window and now - self._minute_window[0] > 60:
                    self._minute_window.popleft()
                while self._hour_window and now - self._hour_window[0] > 3600:
                    self._hour_window.popleft()
                while self._token_window and now - self._token_window[0][0] > 60:
                    self._token_window.popleft()
                minute_ok = len(self._minute_window) < self._limits.requests_per_minute
                hour_ok = len(self._hour_window) < self._limits.requests_per_hour
                tpm = self._limits.tokens_per_minute
                tpm_ok = tpm == 0 or sum(t for _, t in self._token_window) < tpm
                if minute_ok and hour_ok and tpm_ok:
                    self._minute_window.append(now)
                    self._hour_window.append(now)
                    return
                waits: list[float] = []
                if not minute_ok:
                    waits.append(60 - (now - self._minute_window[0]))
                if not hour_ok:
                    waits.append(3600 - (now - self._hour_window[0]))
                if not tpm_ok and self._token_window:
                    waits.append(60 - (now - self._token_window[0][0]))
            time.sleep(max(0.1, min(waits)))

    def _run_with_retry(
        self, api_call: Callable, args: tuple, kwargs: dict, agent_name: str, model: str
    ) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self._limits.max_retries + 1):
            start = time.monotonic()
            try:
                response = api_call(*args, **kwargs)
                self._log(agent_name, model, self._tokens(response), time.monotonic() - start, True)
                return response
            except Exception as exc:
                last_exc = exc
                code = getattr(exc, "status_code", None)
                if code is not None and code not in TRANSIENT_HTTP_CODES:
                    self._log(agent_name, model, (0, 0), time.monotonic() - start, False)
                    raise ApiCallFailedError(str(exc)) from exc
                if attempt < self._limits.max_retries:
                    delay = (self._limits.retry_after_seconds if code == 429
                             else 2 ** attempt + random.uniform(0, 1))
                    time.sleep(delay)
        self._log(agent_name, model, (0, 0), 0.0, False)
        raise ApiCallFailedError(f"Failed after {self._limits.max_retries} retries") from last_exc

    def _tokens(self, response: Any) -> tuple[int, int]:
        usage = getattr(response, "usage", None) or {}
        if isinstance(usage, dict):
            return usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        return getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0)

    def _log(self, agent: str, model: str, tokens: tuple[int, int], dur: float, ok: bool) -> None:
        record = CallRecord(
            call_id=str(uuid.uuid4()),
            agent_name=agent,
            model=model,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=dur,
            success=ok,
        )
        with self._lock:
            self._records.append(record)
            if ok:
                self._token_window.append((time.monotonic(), tokens[0] + tokens[1]))

    def get_call_records(self) -> list[CallRecord]:
        with self._lock:
            return list(self._records)

    def get_token_stats(self) -> TokenStats:
        records = self.get_call_records()
        n = len(records)
        ti = sum(r.input_tokens for r in records)
        to_ = sum(r.output_tokens for r in records)
        return TokenStats(
            calls_count=n,
            total_input_tokens=ti,
            total_output_tokens=to_,
            avg_input_tokens=ti / n if n else 0.0,
            avg_output_tokens=to_ / n if n else 0.0,
        )
