from __future__ import annotations

import logging
import os

from crewai import LLM

from article_generator.constants import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_GEMINI_MODEL,
    LLM_PROVIDER_CLAUDE,
    LLM_PROVIDERS_SUPPORTED,
)

logger = logging.getLogger(__name__)


def build_llm(temperature: float = 0.7) -> LLM:
    """Return a crewai.LLM instance based on the ACTIVE_LLM environment variable.

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


def _build_claude(temperature: float) -> LLM:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise OSError(
            "LLM_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=claude. Add it to your .env file."
        )
    logger.info("LLM provider: Claude (%s)", DEFAULT_CLAUDE_MODEL)
    return LLM(model=DEFAULT_CLAUDE_MODEL, api_key=api_key, temperature=temperature)


def _build_gemini(temperature: float) -> LLM:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise OSError(
            "GEMINI_API_KEY environment variable not set. "
            "Required when ACTIVE_LLM=gemini. Add it to your .env file."
        )
    logger.info("LLM provider: Gemini (%s)", DEFAULT_GEMINI_MODEL)
    return LLM(model=DEFAULT_GEMINI_MODEL, api_key=api_key, temperature=temperature)
