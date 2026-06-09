from __future__ import annotations

# Integration tests — T-072
#
# Verify that the cross_model_comparison field in a generated CostReport covers
# ≥ 3 LLM providers (Anthropic, Google, OpenAI) using the real model_pricing.json.
#
# DoD: cross_model_comparison.entries has ≥ 3 ModelCostEntry items with
#      different provider values.

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from article_generator.services.cost_tracker import CostReport, CostTracker, ModelCostEntry
from article_generator.shared.gatekeeper_models import CallRecord

_PRICING_PATH = Path(__file__).parent.parent.parent / "config" / "model_pricing.json"

pytestmark = pytest.mark.skipif(
    not _PRICING_PATH.exists(),
    reason="config/model_pricing.json not found",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tracker(records: list[CallRecord] | None = None) -> CostTracker:
    gk = MagicMock()
    gk.get_call_records.return_value = records or []
    return CostTracker(gatekeeper=gk, pricing_path=_PRICING_PATH)


def _make_record(model: str, input_tokens: int = 1000, output_tokens: int = 500) -> CallRecord:
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


@pytest.fixture(scope="module")
def report_empty() -> CostReport:
    """Report with no call records — tests comparison projection with zero tokens."""
    return _make_tracker().generate_report()


@pytest.fixture(scope="module")
def report_with_calls() -> CostReport:
    """Report with real call records across multiple models."""
    records = [
        _make_record("claude-sonnet-4-6", input_tokens=5000, output_tokens=2000),
        _make_record("claude-haiku-4-5", input_tokens=3000, output_tokens=1000),
        _make_record("gpt-4o-mini", input_tokens=4000, output_tokens=1500),
    ]
    return _make_tracker(records).generate_report()


# ---------------------------------------------------------------------------
# cross_model_comparison structure
# ---------------------------------------------------------------------------


def test_cross_model_comparison_is_present(report_empty):
    assert report_empty.cross_model_comparison is not None


def test_cross_model_comparison_has_entries(report_empty):
    assert isinstance(report_empty.cross_model_comparison.entries, list)


def test_cross_model_comparison_entries_are_model_cost_entries(report_empty):
    for entry in report_empty.cross_model_comparison.entries:
        assert isinstance(entry, ModelCostEntry)


# ---------------------------------------------------------------------------
# T-072 DoD: ≥ 3 different providers
# ---------------------------------------------------------------------------


def test_cross_model_comparison_covers_at_least_three_providers_empty(report_empty):
    """DoD: ≥ 3 providers even with zero token usage."""
    providers = {e.provider for e in report_empty.cross_model_comparison.entries}
    assert len(providers) >= 3, (
        f"Expected ≥ 3 providers in cross_model_comparison, got: {providers}"
    )


def test_cross_model_comparison_covers_at_least_three_providers_with_calls(report_with_calls):
    """DoD: ≥ 3 providers when the pipeline has real call records."""
    providers = {e.provider for e in report_with_calls.cross_model_comparison.entries}
    assert len(providers) >= 3, (
        f"Expected ≥ 3 providers in cross_model_comparison, got: {providers}"
    )


def test_cross_model_comparison_includes_anthropic(report_empty):
    providers = {e.provider for e in report_empty.cross_model_comparison.entries}
    assert "Anthropic" in providers


def test_cross_model_comparison_includes_google(report_empty):
    providers = {e.provider for e in report_empty.cross_model_comparison.entries}
    assert "Google" in providers


def test_cross_model_comparison_includes_openai(report_empty):
    providers = {e.provider for e in report_empty.cross_model_comparison.entries}
    assert "OpenAI" in providers


# ---------------------------------------------------------------------------
# Entry count — all 7 models from model_pricing.json
# ---------------------------------------------------------------------------


def test_cross_model_comparison_covers_all_seven_models(report_empty):
    assert len(report_empty.cross_model_comparison.entries) == 7


def test_cross_model_comparison_entry_model_ids_are_unique(report_empty):
    ids = [e.model_id for e in report_empty.cross_model_comparison.entries]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Cost projection accuracy with real tokens
# ---------------------------------------------------------------------------


def test_cross_model_comparison_tokens_match_report_totals(report_with_calls):
    cmc = report_with_calls.cross_model_comparison
    assert cmc.total_input_tokens == report_with_calls.total_input_tokens
    assert cmc.total_output_tokens == report_with_calls.total_output_tokens


def test_cross_model_comparison_haiku_cheapest_anthropic(report_with_calls):
    """Haiku should be cheaper than Sonnet and Opus for same token volume."""
    entries = {e.model_id: e for e in report_with_calls.cross_model_comparison.entries}
    assert entries["claude-haiku-4-5"].cost_usd <= entries["claude-sonnet-4-6"].cost_usd
    assert entries["claude-sonnet-4-6"].cost_usd <= entries["claude-opus-4-7"].cost_usd


def test_cross_model_comparison_costs_are_non_negative(report_with_calls):
    for entry in report_with_calls.cross_model_comparison.entries:
        assert entry.cost_usd >= 0.0


def test_cross_model_comparison_zero_tokens_means_zero_cost(report_empty):
    for entry in report_empty.cross_model_comparison.entries:
        assert entry.cost_usd == 0.0
