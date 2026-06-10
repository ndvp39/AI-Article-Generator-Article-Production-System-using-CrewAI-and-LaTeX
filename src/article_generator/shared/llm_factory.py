from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from crewai import LLM

from article_generator.constants import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_GEMINI_MODEL,
    LLM_PROVIDER_CLAUDE,
    LLM_PROVIDERS_SUPPORTED,
    RESULTS_DIR,
)

logger = logging.getLogger(__name__)

# Gemini free tier requires ~60 s wait after a 429 RESOURCE_EXHAUSTED.
_BACKOFF_BASE: int = 60
_BACKOFF_CAP: int = 300
# Hard limit on rate-limit retries per call — prevents runaway loops when the
# daily quota is truly exhausted (no amount of waiting will fix it).
_BACKOFF_MAX_RETRIES: int = 20


def _is_rate_limited(exc: Exception) -> bool:
    """Return True for 429 / RESOURCE_EXHAUSTED errors from any LLM provider."""
    if getattr(exc, "status_code", None) == 429:
        return True
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _call_with_retry(call_fn, messages, *args, **kwargs) -> Any:
    """Invoke call_fn(messages, ...) with exponential backoff on 429.

    Gives up after _BACKOFF_MAX_RETRIES attempts to prevent infinite loops when
    the daily quota is exhausted.  Non-rate-limit errors are re-raised immediately.
    """
    backoff = _BACKOFF_BASE
    attempt = 0
    while True:
        try:
            return call_fn(messages, *args, **kwargs)
        except Exception as exc:
            if _is_rate_limited(exc):
                if attempt >= _BACKOFF_MAX_RETRIES:
                    logger.error(
                        "LLM rate-limited — exhausted %d retries, giving up",
                        _BACKOFF_MAX_RETRIES,
                    )
                    raise
                logger.warning(
                    "LLM rate-limited — backing off %.0fs (attempt %d/%d)",
                    backoff,
                    attempt + 1,
                    _BACKOFF_MAX_RETRIES,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_CAP)
                attempt += 1
                continue
            raise


_AGENT_COSTS_DIR = RESULTS_DIR / "agent_costs"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def _append_cost_record(agent_name: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """Append one call record to results/agent_costs/<agent_name>.jsonl."""
    try:
        _AGENT_COSTS_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "agent_name": agent_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "timestamp": time.time(),
        }
        path = _AGENT_COSTS_DIR / f"{agent_name}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("_append_cost_record failed: %s", exc)


def _inject_retry(llm: Any, agent_name: str = "", model: str = "") -> None:
    """Replace llm.call in-place with a 429-retrying version.

    Also guards against a trailing assistant-role message in the messages list,
    which Claude and Gemini both reject as the final message in a conversation.
    This covers crewai's internal force_final_answer mechanism and any other
    caller that inadvertently ends a conversation with an assistant message.

    Additionally writes per-call token estimates to results/agent_costs/ for
    subprocess cost aggregation.

    BaseLLM.__setattr__ falls back to object.__setattr__ for non-field attributes,
    so this works on any native provider (Gemini, Anthropic, …) regardless of
    which concrete class LLM.__new__ returned.
    """
    original_call = llm.call

    def _retry_call(messages, *args, **kwargs):
        # Ensure the conversation never ends with an assistant/model message.
        # LLMs require the last message to be from the user role.
        if messages and isinstance(messages[-1], dict):
            last_role = messages[-1].get("role", "")
            if last_role in ("assistant", "model"):
                messages = list(messages)
                messages[-1] = dict(messages[-1], role="user")
        response = _call_with_retry(original_call, messages, *args, **kwargs)
        # Estimate tokens from message text and response for cost tracking.
        if agent_name:
            input_text = " ".join(
                m.get("content", "") if isinstance(m, dict) else str(m)
                for m in (messages or [])
            )
            output_text = response if isinstance(response, str) else str(response or "")
            _append_cost_record(
                agent_name, model,
                _estimate_tokens(input_text),
                _estimate_tokens(output_text),
            )
        return response

    llm.call = _retry_call


def build_llm(temperature: float = 0.7, agent_name: str = "") -> Any:
    """Return a rate-limit-resilient LLM based on the ACTIVE_LLM env variable.

    ACTIVE_LLM=gemini  →  uses GEMINI_API_KEY + gemini/gemini-2.0-flash  (default)
    ACTIVE_LLM=claude  →  uses LLM_API_KEY  + anthropic/claude-sonnet-4-6

    agent_name is used for per-call cost tracking in subprocesses.
    """
    provider = os.environ.get("ACTIVE_LLM", LLM_PROVIDER_CLAUDE).lower().strip()

    if provider not in LLM_PROVIDERS_SUPPORTED:
        raise ValueError(
            f"ACTIVE_LLM='{provider}' is not supported. "
            f"Valid values: {sorted(LLM_PROVIDERS_SUPPORTED)}"
        )

    if provider == LLM_PROVIDER_CLAUDE:
        return _build_claude(temperature, agent_name)
    return _build_gemini(temperature, agent_name)


def _build_claude(temperature: float, agent_name: str = "") -> Any:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise OSError(
            "LLM_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=claude. Add it to your .env file."
        )
    logger.info("LLM provider: Claude (%s)", DEFAULT_CLAUDE_MODEL)
    llm = LLM(model=DEFAULT_CLAUDE_MODEL, api_key=api_key, temperature=temperature)
    _inject_retry(llm, agent_name=agent_name, model=DEFAULT_CLAUDE_MODEL)
    return llm


def _build_gemini(temperature: float, agent_name: str = "") -> Any:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise OSError(
            "GEMINI_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=gemini. Add it to your .env file."
        )
    logger.info("LLM provider: Gemini (%s)", DEFAULT_GEMINI_MODEL)
    llm = LLM(model=DEFAULT_GEMINI_MODEL, api_key=api_key, temperature=temperature)
    _inject_retry(llm, agent_name=agent_name, model=DEFAULT_GEMINI_MODEL)
    return llm
