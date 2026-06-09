from __future__ import annotations

import logging
import os
import time
from typing import Any

from crewai import LLM

from article_generator.constants import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_GEMINI_MODEL,
    LLM_PROVIDER_CLAUDE,
    LLM_PROVIDERS_SUPPORTED,
)

logger = logging.getLogger(__name__)

_BACKOFF_BASE: int = 5
_BACKOFF_CAP: int = 300


def _is_rate_limited(exc: Exception) -> bool:
    """Return True for 429 / RESOURCE_EXHAUSTED errors from any LLM provider."""
    if getattr(exc, "status_code", None) == 429:
        return True
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _call_with_retry(call_fn, messages, *args, **kwargs) -> Any:
    """Invoke call_fn(messages, ...) with infinite exponential backoff on 429."""
    backoff = _BACKOFF_BASE
    attempt = 0
    while True:
        try:
            return call_fn(messages, *args, **kwargs)
        except Exception as exc:
            if _is_rate_limited(exc):
                logger.warning(
                    "LLM rate-limited — backing off %.0fs (attempt %d)",
                    backoff, attempt + 1,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_CAP)
                attempt += 1
                continue
            raise


class _RetryingLLM(LLM):
    """Subclass of crewai.LLM that overrides call() with infinite 429 backoff.

    Passes Pydantic validation on Agent(llm=...) because it IS a BaseLLM.
    """

    def call(self, messages, *args, **kwargs) -> Any:
        return _call_with_retry(super().call, messages, *args, **kwargs)


def build_llm(temperature: float = 0.7) -> _RetryingLLM:
    """Return a rate-limit-resilient LLM based on the ACTIVE_LLM env variable.

    ACTIVE_LLM=claude  →  uses LLM_API_KEY  + claude-sonnet-4-6
    ACTIVE_LLM=gemini  →  uses GEMINI_API_KEY + gemini/gemini-2.0-flash
    Defaults to claude if ACTIVE_LLM is not set.
    """
    provider = os.environ.get("ACTIVE_LLM", LLM_PROVIDER_CLAUDE).lower().strip()

    if provider not in LLM_PROVIDERS_SUPPORTED:
        raise ValueError(
            f"ACTIVE_LLM='{provider}' is not supported. "
            f"Valid values: {sorted(LLM_PROVIDERS_SUPPORTED)}"
        )

    if provider == LLM_PROVIDER_CLAUDE:
        return _build_claude(temperature)
    return _build_gemini(temperature)


def _build_claude(temperature: float) -> _RetryingLLM:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise OSError(
            "LLM_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=claude. Add it to your .env file."
        )
    logger.info("LLM provider: Claude (%s)", DEFAULT_CLAUDE_MODEL)
    return _RetryingLLM(model=DEFAULT_CLAUDE_MODEL, api_key=api_key, temperature=temperature)


def _build_gemini(temperature: float) -> _RetryingLLM:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise OSError(
            "GEMINI_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=gemini. Add it to your .env file."
        )
    logger.info("LLM provider: Gemini (%s)", DEFAULT_GEMINI_MODEL)
    return _RetryingLLM(model=DEFAULT_GEMINI_MODEL, api_key=api_key, temperature=temperature)
