from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

_BASE = "article_generator.shared.llm_factory"


@pytest.fixture(autouse=True)
def patch_llm():
    """Always mock crewai.LLM so no real API calls are made."""
    with patch(f"{_BASE}.LLM") as mock_cls:
        mock_cls.return_value = MagicMock()
        yield mock_cls


# ---------------------------------------------------------------------------
# build_llm — provider routing
# ---------------------------------------------------------------------------


def test_build_llm_defaults_to_claude_when_env_unset(patch_llm):
    from article_generator.shared.llm_factory import build_llm
    with patch("os.environ.get", side_effect=lambda k, d=None: {"LLM_API_KEY": "sk-test"}.get(k, d)):
        build_llm()
    assert patch_llm.called
    call_kwargs = patch_llm.call_args.kwargs
    assert "claude" in call_kwargs.get("model", "").lower()


def test_build_llm_claude_uses_llm_api_key(patch_llm, monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "claude")
    monkeypatch.setenv("LLM_API_KEY", "sk-my-key")
    from article_generator.shared.llm_factory import build_llm
    build_llm()
    assert patch_llm.call_args.kwargs["api_key"] == "sk-my-key"


def test_build_llm_gemini_uses_gemini_api_key(patch_llm, monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gm-key")
    from article_generator.shared.llm_factory import build_llm
    build_llm()
    call_kwargs = patch_llm.call_args.kwargs
    assert "gemini" in call_kwargs.get("model", "").lower()
    assert call_kwargs["api_key"] == "gm-key"


def test_build_llm_passes_temperature(patch_llm, monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "claude")
    monkeypatch.setenv("LLM_API_KEY", "sk-key")
    from article_generator.shared.llm_factory import build_llm
    build_llm(temperature=0.3)
    assert patch_llm.call_args.kwargs["temperature"] == 0.3


def test_build_llm_raises_on_unsupported_provider(monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "openai")
    from article_generator.shared.llm_factory import build_llm
    with pytest.raises(ValueError, match="not supported"):
        build_llm()


def test_build_llm_raises_oserror_when_claude_key_missing(monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "claude")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from article_generator.shared.llm_factory import build_llm
    with pytest.raises(OSError, match="LLM_API_KEY"):
        build_llm()


def test_build_llm_raises_oserror_when_gemini_key_missing(monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from article_generator.shared.llm_factory import build_llm
    with pytest.raises(OSError, match="GEMINI_API_KEY"):
        build_llm()


def test_build_llm_returns_llm_instance(patch_llm, monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM", "claude")
    monkeypatch.setenv("LLM_API_KEY", "sk-key")
    from article_generator.shared.llm_factory import build_llm
    result = build_llm()
    assert result is patch_llm.return_value
