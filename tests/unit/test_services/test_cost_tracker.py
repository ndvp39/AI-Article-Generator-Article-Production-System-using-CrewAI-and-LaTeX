from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.cost_tracker import (
    CostReport,
    CostTracker,
    CrossModelComparison,
)
from article_generator.shared.gatekeeper_models import CallRecord


@pytest.fixture(autouse=True)
def _no_subprocess_records():
    """Prevent tests from reading real results/agent_costs/ files on disk."""
    with patch("article_generator.services.cost_tracker.load_subprocess_records", return_value=[]):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_PRICING = {
    "model_pricing": {
        "version": "1.00",
        "currency": "USD",
        "unit": "per_million_tokens",
        "models": {
            "model-a": {
                "display_name": "Model A",
                "provider": "ProviderX",
                "input_price_per_mtok": 1.0,
                "output_price_per_mtok": 2.0,
            },
            "model-b": {
                "display_name": "Model B",
                "provider": "ProviderY",
                "input_price_per_mtok": 4.0,
                "output_price_per_mtok": 8.0,
            },
            "model-c": {
                "display_name": "Model C",
                "provider": "ProviderZ",
                "input_price_per_mtok": 10.0,
                "output_price_per_mtok": 20.0,
            },
        },
    }
}

_FULL_PRICING_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "model_pricing.json"
)


def _make_record(
    agent: str = "agent",
    model: str = "model-a",
    input_tokens: int = 1_000,
    output_tokens: int = 500,
    duration: float = 1.0,
) -> CallRecord:
    return CallRecord(
        call_id="id",
        agent_name=agent,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp="2026-01-01T00:00:00+00:00",
        duration_seconds=duration,
        success=True,
    )


@pytest.fixture()
def pricing_file(tmp_path: Path) -> Path:
    p = tmp_path / "model_pricing.json"
    p.write_text(json.dumps(_MINIMAL_PRICING), encoding="utf-8")
    return p


def _tracker(records: list[CallRecord], pricing_path: Path, budget: float = 1.0) -> CostTracker:
    gk = MagicMock()
    gk.get_call_records.return_value = records
    return CostTracker(gatekeeper=gk, pricing_path=pricing_path, budget_alert_usd=budget)


# ---------------------------------------------------------------------------
# _load_pricing
# ---------------------------------------------------------------------------


def test_load_pricing_reads_models(pricing_file):
    t = _tracker([], pricing_file)
    assert "model-a" in t._pricing
    assert "model-b" in t._pricing


def test_load_pricing_stores_prices(pricing_file):
    t = _tracker([], pricing_file)
    assert t._pricing["model-a"]["input_price_per_mtok"] == 1.0
    assert t._pricing["model-a"]["output_price_per_mtok"] == 2.0


# ---------------------------------------------------------------------------
# _cost_for_record
# ---------------------------------------------------------------------------


def test_cost_for_record_known_model(pricing_file):
    # 1000 input @ $1/Mtok + 500 output @ $2/Mtok = $0.001 + $0.001 = $0.002
    t = _tracker([], pricing_file)
    rec = _make_record(input_tokens=1_000, output_tokens=500, model="model-a")
    assert t._cost_for_record(rec) == pytest.approx(0.000_001 * 1_000 + 0.000_002 * 500)


def test_cost_for_record_unknown_model_returns_zero(pricing_file):
    t = _tracker([], pricing_file)
    rec = _make_record(model="unknown-model")
    assert t._cost_for_record(rec) == 0.0


def test_cost_for_record_zero_tokens(pricing_file):
    t = _tracker([], pricing_file)
    rec = _make_record(input_tokens=0, output_tokens=0)
    assert t._cost_for_record(rec) == 0.0


# ---------------------------------------------------------------------------
# check_budget_alert
# ---------------------------------------------------------------------------


def test_check_budget_alert_returns_false_below_threshold(pricing_file):
    rec = _make_record(input_tokens=100, output_tokens=50)
    t = _tracker([rec], pricing_file, budget=100.0)
    assert t.check_budget_alert(100.0) is False


def test_check_budget_alert_returns_true_at_threshold(pricing_file):
    # 1_000_000 input @ $1/Mtok = $1.00 — exactly at threshold
    rec = _make_record(input_tokens=1_000_000, output_tokens=0)
    t = _tracker([rec], pricing_file, budget=1.0)
    assert t.check_budget_alert(1.0) is True


def test_check_budget_alert_returns_true_above_threshold(pricing_file):
    rec = _make_record(input_tokens=2_000_000, output_tokens=0)
    t = _tracker([rec], pricing_file, budget=1.0)
    assert t.check_budget_alert(1.0) is True


def test_check_budget_alert_logs_warning_when_triggered(pricing_file, caplog):
    rec = _make_record(input_tokens=2_000_000, output_tokens=0)
    t = _tracker([rec], pricing_file, budget=1.0)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        t.check_budget_alert(1.0)
    assert any("budget alert" in m.lower() for m in caplog.messages)


# ---------------------------------------------------------------------------
# compare_models
# ---------------------------------------------------------------------------


def test_compare_models_returns_crossmodelcomparison(pricing_file):
    t = _tracker([], pricing_file)
    result = t.compare_models(["model-a", "model-b"], total_input_tokens=1000, total_output_tokens=500)
    assert isinstance(result, CrossModelComparison)


def test_compare_models_entries_count(pricing_file):
    t = _tracker([], pricing_file)
    result = t.compare_models(
        ["model-a", "model-b", "model-c"],
        total_input_tokens=1000,
        total_output_tokens=500,
    )
    assert len(result.entries) == 3


def test_compare_models_skips_unknown_model_with_warning(pricing_file, caplog):
    t = _tracker([], pricing_file)
    with caplog.at_level(logging.WARNING, logger="article_generator.services.cost_tracker"):
        result = t.compare_models(
            ["model-a", "no-such-model"],
            total_input_tokens=1000,
            total_output_tokens=500,
        )
    assert len(result.entries) == 1
    assert any("no-such-model" in m for m in caplog.messages)


def test_compare_models_cost_accuracy(pricing_file):
    # model-b: input=$4/Mtok, output=$8/Mtok
    # 1_000_000 input + 500_000 output = $4.00 + $4.00 = $8.00
    t = _tracker([], pricing_file)
    result = t.compare_models(
        ["model-b"],
        total_input_tokens=1_000_000,
        total_output_tokens=500_000,
    )
    assert result.entries[0].cost_usd == pytest.approx(8.0, rel=1e-5)


def test_compare_models_uses_records_when_tokens_not_provided(pricing_file):
    rec = _make_record(input_tokens=500_000, output_tokens=250_000)
    t = _tracker([rec], pricing_file)
    result = t.compare_models(["model-a"])
    assert result.total_input_tokens == 500_000
    assert result.total_output_tokens == 250_000


def test_compare_models_covers_three_providers(pricing_file):
    t = _tracker([], pricing_file)
    result = t.compare_models(
        ["model-a", "model-b", "model-c"],
        total_input_tokens=1000,
        total_output_tokens=500,
    )
    providers = {e.provider for e in result.entries}
    assert len(providers) >= 3


# ---------------------------------------------------------------------------
# generate_report — structure
# ---------------------------------------------------------------------------


def test_generate_report_returns_cost_report(pricing_file):
    t = _tracker([], pricing_file)
    assert isinstance(t.generate_report(), CostReport)


def test_generate_report_empty_records(pricing_file):
    report = _tracker([], pricing_file).generate_report()
    assert report.total_calls == 0
    assert report.total_cost_usd == 0.0
    assert report.by_agent == []
    assert report.by_model == []


def test_generate_report_total_calls(pricing_file):
    records = [_make_record() for _ in range(3)]
    report = _tracker(records, pricing_file).generate_report()
    assert report.total_calls == 3


def test_generate_report_total_tokens(pricing_file):
    records = [
        _make_record(input_tokens=1000, output_tokens=200),
        _make_record(input_tokens=3000, output_tokens=800),
    ]
    report = _tracker(records, pricing_file).generate_report()
    assert report.total_input_tokens == 4000
    assert report.total_output_tokens == 1000


def test_generate_report_duration(pricing_file):
    records = [_make_record(duration=1.5), _make_record(duration=2.5)]
    report = _tracker(records, pricing_file).generate_report()
    assert report.duration_seconds == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# generate_report — by_agent aggregation
# ---------------------------------------------------------------------------


def test_generate_report_by_agent_single_entry(pricing_file):
    records = [_make_record(agent="writer", model="model-a")]
    report = _tracker(records, pricing_file).generate_report()
    assert len(report.by_agent) == 1
    assert report.by_agent[0].agent_name == "writer"
    assert report.by_agent[0].calls == 1


def test_generate_report_by_agent_aggregates_same_agent_model(pricing_file):
    records = [
        _make_record(agent="writer", model="model-a", input_tokens=1000, output_tokens=200),
        _make_record(agent="writer", model="model-a", input_tokens=2000, output_tokens=400),
    ]
    report = _tracker(records, pricing_file).generate_report()
    assert len(report.by_agent) == 1
    assert report.by_agent[0].calls == 2
    assert report.by_agent[0].input_tokens == 3000
    assert report.by_agent[0].output_tokens == 600


def test_generate_report_by_agent_separates_different_models(pricing_file):
    records = [
        _make_record(agent="writer", model="model-a"),
        _make_record(agent="writer", model="model-b"),
    ]
    report = _tracker(records, pricing_file).generate_report()
    assert len(report.by_agent) == 2


def test_generate_report_by_agent_cost_rounded_to_6_decimals(pricing_file):
    records = [_make_record(input_tokens=1, output_tokens=1)]
    report = _tracker(records, pricing_file).generate_report()
    cost_str = str(report.by_agent[0].cost_usd)
    decimal_places = len(cost_str.split(".")[-1]) if "." in cost_str else 0
    assert decimal_places <= 6


# ---------------------------------------------------------------------------
# generate_report — by_model aggregation
# ---------------------------------------------------------------------------


def test_generate_report_by_model_groups_by_model_id(pricing_file):
    records = [
        _make_record(agent="a1", model="model-a"),
        _make_record(agent="a2", model="model-a"),
        _make_record(agent="a1", model="model-b"),
    ]
    report = _tracker(records, pricing_file).generate_report()
    model_ids = [e.model_id for e in report.by_model]
    assert "model-a" in model_ids
    assert "model-b" in model_ids
    assert len(report.by_model) == 2


def test_generate_report_by_model_display_name_from_pricing(pricing_file):
    records = [_make_record(model="model-a")]
    report = _tracker(records, pricing_file).generate_report()
    assert report.by_model[0].display_name == "Model A"


def test_generate_report_by_model_provider_from_pricing(pricing_file):
    records = [_make_record(model="model-a")]
    report = _tracker(records, pricing_file).generate_report()
    assert report.by_model[0].provider == "ProviderX"


# ---------------------------------------------------------------------------
# generate_report — cross_model_comparison
# ---------------------------------------------------------------------------


def test_generate_report_has_cross_model_comparison(pricing_file):
    report = _tracker([], pricing_file).generate_report()
    assert isinstance(report.cross_model_comparison, CrossModelComparison)


def test_generate_report_cross_model_covers_all_pricing_models(pricing_file):
    report = _tracker([], pricing_file).generate_report()
    cmc_ids = {e.model_id for e in report.cross_model_comparison.entries}
    assert cmc_ids == {"model-a", "model-b", "model-c"}


# ---------------------------------------------------------------------------
# generate_report — budget alert
# ---------------------------------------------------------------------------


def test_generate_report_budget_not_triggered_when_below(pricing_file):
    report = _tracker([], pricing_file, budget=1.0).generate_report()
    assert report.budget_alert_triggered is False


def test_generate_report_budget_triggered_when_above(pricing_file):
    # 2_000_000 input @ $1/Mtok = $2.00 > $1.00 threshold
    rec = _make_record(input_tokens=2_000_000, output_tokens=0)
    report = _tracker([rec], pricing_file, budget=1.0).generate_report()
    assert report.budget_alert_triggered is True


def test_generate_report_budget_threshold_stored(pricing_file):
    report = _tracker([], pricing_file, budget=0.42).generate_report()
    assert report.budget_alert_threshold_usd == 0.42


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_json_file(pricing_file, tmp_path):
    report = _tracker([], pricing_file).generate_report()
    path = _tracker([], pricing_file).save_report(report, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".json"


def test_save_report_filename_contains_timestamp(pricing_file, tmp_path):
    report = _tracker([], pricing_file).generate_report()
    path = _tracker([], pricing_file).save_report(report, output_dir=tmp_path)
    assert path.name.startswith("cost_report_")


def test_save_report_is_valid_json(pricing_file, tmp_path):
    report = _tracker([], pricing_file).generate_report()
    path = _tracker([], pricing_file).save_report(report, output_dir=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "total_calls" in data
    assert "by_agent" in data
    assert "cross_model_comparison" in data


def test_save_report_returns_path(pricing_file, tmp_path):
    report = _tracker([], pricing_file).generate_report()
    result = _tracker([], pricing_file).save_report(report, output_dir=tmp_path)
    assert isinstance(result, Path)


def test_save_report_uses_results_dir_by_default(pricing_file):
    report = _tracker([], pricing_file).generate_report()
    with patch("article_generator.services.cost_tracker.RESULTS_DIR", new=pricing_file.parent):
        path = _tracker([], pricing_file).save_report(report)
    assert path.parent == pricing_file.parent


# ---------------------------------------------------------------------------
# real pricing file — ≥ 3 providers covered (T-072)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _FULL_PRICING_PATH.exists(),
    reason="config/model_pricing.json not found",
)
def test_real_pricing_covers_three_providers():
    gk = MagicMock()
    gk.get_call_records.return_value = []
    t = CostTracker(gatekeeper=gk, pricing_path=_FULL_PRICING_PATH)
    providers = {v["provider"] for v in t._pricing.values()}
    assert len(providers) >= 3, f"Expected ≥ 3 providers, got: {providers}"


@pytest.mark.skipif(
    not _FULL_PRICING_PATH.exists(),
    reason="config/model_pricing.json not found",
)
def test_real_pricing_comparison_has_seven_models():
    gk = MagicMock()
    gk.get_call_records.return_value = []
    t = CostTracker(gatekeeper=gk, pricing_path=_FULL_PRICING_PATH)
    result = t.compare_models(list(t._pricing.keys()), total_input_tokens=0, total_output_tokens=0)
    assert len(result.entries) == 7
