from __future__ import annotations

import logging
import random
import time
import uuid
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

logger = logging.getLogger(__name__)

_BACKOFF_BASE: int = 5    # initial 429 backoff in seconds
_BACKOFF_MAX: int = 300   # cap at 5 minutes


class ApiGatekeeper:
    def __init__(self, limits: ServiceLimits) -> None:
        self._limits = limits
        self._lock = Lock()
        self._semaphore = Semaphore(limits.concurrent_max)
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
                return self._run_with_retry(api_call, args, kwargs, agent_name, model)
        finally:
            with self._lock:
                self._inflight -= 1

    def _run_with_retry(
        self, api_call: Callable, args: tuple, kwargs: dict, agent_name: str, model: str
    ) -> Any:
        backoff = _BACKOFF_BASE
        attempt = 0
        while True:
            start = time.monotonic()
            try:
                response = api_call(*args, **kwargs)
                self._log(agent_name, model, self._tokens(response), time.monotonic() - start, True)
                return response
            except Exception as exc:
                code = getattr(exc, "status_code", None)
                elapsed = time.monotonic() - start
                if code == 429:
                    logger.warning("429 — backing off %.0fs (attempt %d)", backoff, attempt + 1)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, _BACKOFF_MAX)
                    attempt += 1
                    continue
                if code is not None and code not in TRANSIENT_HTTP_CODES:
                    self._log(agent_name, model, (0, 0), elapsed, False)
                    raise ApiCallFailedError(str(exc)) from exc
                attempt += 1
                if attempt > self._limits.max_retries:
                    self._log(agent_name, model, (0, 0), 0.0, False)
                    raise ApiCallFailedError(f"Failed after {self._limits.max_retries} retries") from exc
                time.sleep(2 ** (attempt - 1) + random.uniform(0, 1))

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
