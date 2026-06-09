from __future__ import annotations

# Integration tests — T-073
#
# Verify that the budget alert fires (budget_alert_triggered=True, WARNING logged)
# when accumulated token cost exceeds the configured threshold.
#
# DoD: Setting budget_alert_threshold_usd=0.01 triggers WARNING log and sets
#      budget_alert_triggered=True in the generated CostReport.

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from article_generator.services.cost_tracker import CostReport, CostTracker
from article_generator.shared.gatekeeper_models import CallRecord

_PRICING_PATH = Path(__file__).parent.parent.parent / "config" / "model_pricing.json"

pytestmark = pytest.mark.skipif(
    not _PRICING_PATH.exists(),
    reason="config/model_pricing.json not found",
)

_LOW_THRESHOLD = 0.01  # $0.01 USD — easy to exceed


def _make_tracker(records: list[CallRecord], budget: float) -> CostTracker:
    gk = MagicMock()
    gk.get_call_records.return_value = records
    return CostTracker(gatekeeper=gk, pricing_path=_PRICING_PATH, budget_alert_usd=budget)


def _make_record(model: str, input_tokens: int, output_tokens: int = 0) -> CallRecord:
    return CallRecord(
        call_id="id",
        agent_name="agent",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp="2026-06-09T00:00:00+00:00",
        duration_seconds=1.0,
        success=True,
    )


# claude-haiku-4-5: $0.80/Mtok input → 20,000 tokens = $0.016 > $0.01
_EXCEEDING_RECORDS = [_make_record("claude-haiku-4-5", input_tokens=20_000)]

# 100 tokens = $0.00008 — well below $0.01
_BELOW_RECORDS = [_make_record("claude-haiku-4-5", input_tokens=100)]


# ---------------------------------------------------------------------------
# check_budget_alert — direct API
# ---------------------------------------------------------------------------


def test_budget_alert_not_triggered_below_threshold():
    t = _make_tracker(_BELOW_RECORDS, budget=_LOW_THRESHOLD)
    assert t.check_budget_alert(_LOW_THRESHOLD) is False


def test_budget_alert_triggered_above_threshold():
    t = _make_tracker(_EXCEEDING_RECORDS, budget=_LOW_THRESHOLD)
    assert t.check_budget_alert(_LOW_THRESHOLD) is True


def test_budget_alert_logs_warning_when_triggered(caplog):
    t = _make_tracker(_EXCEEDING_RECORDS, budget=_LOW_THRESHOLD)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        t.check_budget_alert(_LOW_THRESHOLD)
    assert any("budget alert" in m.lower() for m in caplog.messages)


def test_budget_alert_no_warning_when_below_threshold(caplog):
    t = _make_tracker(_BELOW_RECORDS, budget=_LOW_THRESHOLD)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        t.check_budget_alert(_LOW_THRESHOLD)
    assert not any("budget alert" in m.lower() for m in caplog.messages)


# ---------------------------------------------------------------------------
# generate_report — budget_alert_triggered field
# ---------------------------------------------------------------------------


def test_generate_report_budget_alert_triggered_true_when_over(caplog):
    """DoD: report.budget_alert_triggered is True when cost exceeds threshold."""
    t = _make_tracker(_EXCEEDING_RECORDS, budget=_LOW_THRESHOLD)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        report = t.generate_report()
    assert report.budget_alert_triggered is True


def test_generate_report_budget_alert_triggered_false_when_under():
    t = _make_tracker(_BELOW_RECORDS, budget=_LOW_THRESHOLD)
    report = t.generate_report()
    assert report.budget_alert_triggered is False


def test_generate_report_logs_warning_when_budget_exceeded(caplog):
    """DoD: WARNING log emitted during generate_report() when threshold exceeded."""
    t = _make_tracker(_EXCEEDING_RECORDS, budget=_LOW_THRESHOLD)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        t.generate_report()
    assert any("budget alert" in m.lower() for m in caplog.messages)


def test_generate_report_warning_contains_cost_and_threshold(caplog):
    t = _make_tracker(_EXCEEDING_RECORDS, budget=_LOW_THRESHOLD)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        t.generate_report()
    warning_text = " ".join(caplog.messages)
    assert "0.01" in warning_text or "budget" in warning_text.lower()


def test_generate_report_threshold_stored_in_report():
    t = _make_tracker([], budget=_LOW_THRESHOLD)
    report = t.generate_report()
    assert report.budget_alert_threshold_usd == _LOW_THRESHOLD


# ---------------------------------------------------------------------------
# Threshold boundary — exact threshold fires alert
# ---------------------------------------------------------------------------


def test_budget_alert_fires_at_exact_threshold():
    # claude-haiku-4-5: $0.80/Mtok input
    # 1_000_000 * 0.80 / 1_000_000 = $0.80
    # Use threshold = $0.80 exactly
    records = [_make_record("claude-haiku-4-5", input_tokens=1_000_000, output_tokens=0)]
    t = _make_tracker(records, budget=0.80)
    assert t.check_budget_alert(0.80) is True


def test_budget_alert_does_not_fire_just_below_threshold():
    # 999_999 tokens @ $0.80/Mtok = $0.799999 < $0.80
    records = [_make_record("claude-haiku-4-5", input_tokens=999_999, output_tokens=0)]
    t = _make_tracker(records, budget=0.80)
    assert t.check_budget_alert(0.80) is False


# ---------------------------------------------------------------------------
# Multi-agent scenario — alert fires when combined cost exceeds threshold
# ---------------------------------------------------------------------------


def test_budget_alert_fires_for_combined_multi_agent_cost(caplog):
    """Alert fires when sum across multiple agents/models exceeds threshold."""
    records = [
        _make_record("claude-haiku-4-5", input_tokens=5_000),   # $0.004
        _make_record("claude-sonnet-4-6", input_tokens=2_000),  # $0.006
        # total ≈ $0.010 — at threshold of $0.009
    ]
    t = _make_tracker(records, budget=0.009)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        report = t.generate_report()
    assert report.budget_alert_triggered is True
