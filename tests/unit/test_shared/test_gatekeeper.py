import re
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

from article_generator.shared.config import ServiceLimits
from article_generator.shared.gatekeeper import ApiGatekeeper
from article_generator.shared.gatekeeper_models import (
    ApiCallFailedError,
    QueueFullError,
    TokenStats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_limits(**overrides) -> ServiceLimits:
    defaults = {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "concurrent_max": 5,
        "retry_after_seconds": 1,
        "max_retries": 2,
        "max_queue_depth": 10,
    }
    defaults.update(overrides)
    return ServiceLimits(**defaults)


def make_gk(**limit_overrides) -> ApiGatekeeper:
    return ApiGatekeeper(make_limits(**limit_overrides))


# ---------------------------------------------------------------------------
# Basic execute
# ---------------------------------------------------------------------------

def test_execute_returns_api_call_result():
    assert make_gk().execute(lambda: 42) == 42


def test_execute_forwards_positional_and_keyword_args():
    received = []
    def api(a, b, *, key):
        received.append((a, b, key))
        return True
    make_gk().execute(api, "x", "y", key="z")
    assert received == [("x", "y", "z")]


# ---------------------------------------------------------------------------
# CallRecord logging
# ---------------------------------------------------------------------------

def test_execute_logs_one_call_record():
    gk = make_gk()
    gk.execute(lambda: None, agent_name="researcher", model="claude-sonnet-4-5")
    records = gk.get_call_records()
    assert len(records) == 1
    r = records[0]
    assert r.agent_name == "researcher"
    assert r.model == "claude-sonnet-4-5"
    assert r.success is True
    assert r.duration_seconds >= 0


def test_call_record_uuid_and_iso_timestamp():
    gk = make_gk()
    gk.execute(lambda: None)
    r = gk.get_call_records()[0]
    assert re.match(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", r.call_id)
    assert "T" in r.timestamp  # ISO-8601 separator


def test_get_call_records_returns_independent_copy():
    gk = make_gk()
    gk.execute(lambda: None)
    copy = gk.get_call_records()
    copy.clear()
    assert len(gk.get_call_records()) == 1


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def test_tokens_extracted_from_dict_usage():
    gk = make_gk()
    resp = MagicMock()
    resp.usage = {"input_tokens": 100, "output_tokens": 200}
    gk.execute(lambda: resp)
    r = gk.get_call_records()[0]
    assert r.input_tokens == 100
    assert r.output_tokens == 200


def test_tokens_extracted_from_object_usage():
    gk = make_gk()
    resp = MagicMock()
    resp.usage.input_tokens = 50
    resp.usage.output_tokens = 75
    gk.execute(lambda: resp)
    r = gk.get_call_records()[0]
    assert r.input_tokens == 50
    assert r.output_tokens == 75


def test_tokens_zero_when_no_usage_attribute():
    gk = make_gk()
    gk.execute(lambda: "plain string")
    r = gk.get_call_records()[0]
    assert r.input_tokens == 0
    assert r.output_tokens == 0


# ---------------------------------------------------------------------------
# Queue / backpressure
# ---------------------------------------------------------------------------

def test_queue_full_raises_when_inflight_at_max():
    gk = make_gk(max_queue_depth=3)
    gk._inflight = 3
    with pytest.raises(QueueFullError, match="3"):
        gk.execute(lambda: None)


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------

def test_retry_on_transient_429_succeeds_eventually():
    attempts = []
    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            err = Exception("rate limited")
            err.status_code = 429
            raise err
        return "ok"

    with patch("article_generator.shared.gatekeeper.time.sleep"):
        result = make_gk(max_retries=3).execute(flaky)

    assert result == "ok"
    assert len(attempts) == 3


def test_no_retry_on_permanent_400():
    attempts = []
    def bad_request():
        attempts.append(1)
        err = Exception("bad request")
        err.status_code = 400
        raise err

    with patch("article_generator.shared.gatekeeper.time.sleep"):
        with pytest.raises(ApiCallFailedError):
            make_gk(max_retries=3).execute(bad_request)

    assert len(attempts) == 1  # fired once, no retries


def test_exhausted_retries_raises_api_call_failed():
    def always_503():
        err = Exception("server error")
        err.status_code = 503
        raise err

    with patch("article_generator.shared.gatekeeper.time.sleep"):
        with pytest.raises(ApiCallFailedError, match="2 retries"):
            make_gk(max_retries=2).execute(always_503)


def test_failed_call_logs_record_with_success_false():
    def always_fails():
        err = Exception("oops")
        err.status_code = 500
        raise err

    with patch("article_generator.shared.gatekeeper.time.sleep"):
        gk = make_gk(max_retries=1)
        with pytest.raises(ApiCallFailedError):
            gk.execute(always_fails, agent_name="editor")

    r = gk.get_call_records()[0]
    assert r.success is False
    assert r.agent_name == "editor"


# ---------------------------------------------------------------------------
# Token stats
# ---------------------------------------------------------------------------

def test_token_stats_aggregates_correctly():
    gk = make_gk()
    for _ in range(3):
        resp = MagicMock()
        resp.usage = {"input_tokens": 10, "output_tokens": 20}
        gk.execute(lambda r=resp: r)
    stats = gk.get_token_stats()
    assert stats.calls_count == 3
    assert stats.total_input_tokens == 30
    assert stats.total_output_tokens == 60
    assert stats.total_tokens == 90
    assert stats.avg_input_tokens == 10.0
    assert stats.avg_output_tokens == 20.0


def test_token_stats_empty_returns_zeros():
    stats = make_gk().get_token_stats()
    assert stats.calls_count == 0
    assert stats.total_tokens == 0
    assert stats.avg_input_tokens == 0.0
    assert stats.avg_output_tokens == 0.0


def test_token_stats_total_tokens_property():
    stats = TokenStats(
        calls_count=1,
        total_input_tokens=100,
        total_output_tokens=200,
        avg_input_tokens=100.0,
        avg_output_tokens=200.0,
    )
    assert stats.total_tokens == 300


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

def test_concurrent_calls_all_logged():
    gk = make_gk(concurrent_max=10, requests_per_minute=1000)
    errors: list[Exception] = []

    def call():
        try:
            gk.execute(lambda: None, agent_name="thread")
        except Exception as exc:
            errors.append(exc)

    threads = [Thread(target=call) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(gk.get_call_records()) == 10


# ---------------------------------------------------------------------------
# 429 infinite exponential backoff
# ---------------------------------------------------------------------------

def test_429_backoff_starts_at_base_seconds():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 2:
            err = Exception("rate limited")
            err.status_code = 429
            raise err
        return "ok"

    slept = []
    with patch("article_generator.shared.gatekeeper.time.sleep", side_effect=lambda d: slept.append(d)):
        make_gk(max_retries=3).execute(flaky)

    assert slept[0] == 5  # _BACKOFF_BASE


def test_429_backoff_doubles_each_attempt():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 4:
            err = Exception("rate limited")
            err.status_code = 429
            raise err
        return "ok"

    slept = []
    with patch("article_generator.shared.gatekeeper.time.sleep", side_effect=lambda d: slept.append(d)):
        make_gk(max_retries=1).execute(flaky)

    assert slept == [5, 10, 20]


def test_429_retries_infinitely_not_bounded_by_max_retries():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) <= 5:
            err = Exception("rate limited")
            err.status_code = 429
            raise err
        return "ok"

    with patch("article_generator.shared.gatekeeper.time.sleep"):
        result = make_gk(max_retries=1).execute(flaky)

    assert result == "ok"
    assert len(attempts) == 6  # 5 failures + 1 success


# ---------------------------------------------------------------------------
# Non-429 uses exponential backoff
# ---------------------------------------------------------------------------

def test_non_429_uses_exponential_backoff():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 2:
            err = Exception("server error")
            err.status_code = 503
            raise err
        return "ok"

    slept = []
    with patch("article_generator.shared.gatekeeper.time.sleep", side_effect=lambda d: slept.append(d)), \
         patch("article_generator.shared.gatekeeper.random.uniform", return_value=0.0):
        make_gk(max_retries=3, retry_after_seconds=99).execute(flaky)

    assert slept[0] == 1.0  # 2**0 + 0.0, not retry_after_seconds=99
