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


def test_build_llm_injects_retry_into_call(patch_llm, monkeypatch):
    """After build_llm(), llm.call should be our retry wrapper, not the original."""
    monkeypatch.setenv("ACTIVE_LLM", "claude")
    monkeypatch.setenv("LLM_API_KEY", "sk-key")
    original_call = MagicMock(return_value="original")
    patch_llm.return_value.call = original_call
    from article_generator.shared.llm_factory import build_llm
    result = build_llm()
    # After injection the call attribute must be a different callable
    assert result.call is not original_call


# ---------------------------------------------------------------------------
# _call_with_retry — 429 backoff behaviour
# ---------------------------------------------------------------------------


def test_call_with_retry_retries_on_429_and_eventually_succeeds():
    import article_generator.shared.llm_factory as factory_module
    from article_generator.shared.llm_factory import _call_with_retry

    calls = []

    def flaky(messages, *a, **kw):
        calls.append(1)
        if len(calls) < 3:
            raise Exception("429 RESOURCE_EXHAUSTED")
        return "ok"

    with patch.object(factory_module.time, "sleep"):
        result = _call_with_retry(flaky, ["msg"])

    assert result == "ok"
    assert len(calls) == 3


def test_call_with_retry_raises_non_429_immediately():
    from article_generator.shared.llm_factory import _call_with_retry

    def bad_call(messages, *a, **kw):
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        _call_with_retry(bad_call, ["msg"])


def test_call_with_retry_backoff_doubles_each_attempt():
    import article_generator.shared.llm_factory as factory_module
    from article_generator.shared.llm_factory import _BACKOFF_BASE, _call_with_retry

    sleep_calls = []
    attempts = [0]

    def flaky(messages, *a, **kw):
        attempts[0] += 1
        if attempts[0] < 4:
            raise Exception("429")
        return "done"

    with patch.object(factory_module.time, "sleep", side_effect=lambda s: sleep_calls.append(s)):
        _call_with_retry(flaky, ["msg"])

    assert sleep_calls[0] == _BACKOFF_BASE
    assert sleep_calls[1] == _BACKOFF_BASE * 2
    assert sleep_calls[2] == _BACKOFF_BASE * 4
