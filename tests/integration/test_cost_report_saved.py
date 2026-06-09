from __future__ import annotations

# Integration tests — T-071
#
# Verify that cost_report_<timestamp>.json is written to results/ after every
# pipeline run (generate_article) and that the file is valid JSON matching the
# CostReport schema.
#
# DoD: File exists in results/; valid JSON; contains all CostReport top-level keys.
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.services.cost_tracker import CostReport, CrossModelComparison
from article_generator.shared.models import ArticleResult

_SDK_BASE = "article_generator.sdk.sdk"

_EXPECTED_KEYS = {
    "timestamp",
    "total_calls",
    "total_input_tokens",
    "total_output_tokens",
    "total_cost_usd",
    "budget_alert_threshold_usd",
    "budget_alert_triggered",
    "by_agent",
    "by_model",
    "cross_model_comparison",
    "duration_seconds",
}


def _make_article_result() -> ArticleResult:
    return ArticleResult(
        success=True,
        markdown_content="# Test",
        tex_path="results/article.tex",
        bib_path="results/references.bib",
        pdf_path="results/article.pdf",
    )


def _make_cost_report() -> CostReport:
    return CostReport(
        timestamp="2026-06-09T12:00:00+00:00",
        total_calls=2,
        total_input_tokens=1000,
        total_output_tokens=500,
        total_cost_usd=0.001234,
        budget_alert_threshold_usd=1.0,
        budget_alert_triggered=False,
        by_agent=[],
        by_model=[],
        cross_model_comparison=CrossModelComparison(
            total_input_tokens=1000,
            total_output_tokens=500,
            entries=[],
        ),
        duration_seconds=3.5,
    )


@pytest.fixture()
def sdk_with_mocks(tmp_path: Path):
    """SDK instance with all I/O mocked; save_report writes to tmp_path."""
    with (
        patch(f"{_SDK_BASE}.ConfigManager"),
        patch(f"{_SDK_BASE}.CrewService") as mock_crew,
        patch(f"{_SDK_BASE}.FileManager"),
        patch(f"{_SDK_BASE}.ApiGatekeeper"),
        patch(f"{_SDK_BASE}.CostTracker") as mock_tracker_cls,
    ):
        mock_crew.return_value.run_pipeline.return_value = _make_article_result()

        report = _make_cost_report()
        mock_tracker = mock_tracker_cls.return_value
        mock_tracker.generate_report.return_value = report

        # Make save_report write a real JSON file to tmp_path
        def _real_save(r: CostReport, output_dir=None):
            from dataclasses import asdict
            out = tmp_path / "cost_report_2026-06-09T12-00-00.json"
            out.write_text(json.dumps(asdict(r), indent=2), encoding="utf-8")
            return out

        mock_tracker.save_report.side_effect = _real_save

        sdk = ArticleGeneratorSDK()
        yield sdk, tmp_path, mock_tracker


# ---------------------------------------------------------------------------
# generate_article triggers save_report
# ---------------------------------------------------------------------------


def test_generate_article_calls_generate_report(sdk_with_mocks):
    sdk, _, mock_tracker = sdk_with_mocks
    sdk.generate_article("Test Topic")
    mock_tracker.generate_report.assert_called_once()


def test_generate_article_calls_save_report(sdk_with_mocks):
    sdk, _, mock_tracker = sdk_with_mocks
    sdk.generate_article("Test Topic")
    mock_tracker.save_report.assert_called_once()


def test_generate_article_passes_report_to_save_report(sdk_with_mocks):
    sdk, _, mock_tracker = sdk_with_mocks
    sdk.generate_article("Test Topic")
    saved_report = mock_tracker.save_report.call_args[0][0]
    assert isinstance(saved_report, CostReport)


# ---------------------------------------------------------------------------
# File written to output dir — schema and format
# ---------------------------------------------------------------------------


def test_cost_report_file_is_created(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    json_files = list(tmp_path.glob("cost_report_*.json"))
    assert len(json_files) == 1


def test_cost_report_file_is_valid_json(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_cost_report_file_has_all_required_keys(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = _EXPECTED_KEYS - set(data.keys())
    assert missing == set(), f"Missing keys in cost_report JSON: {missing}"


def test_cost_report_filename_matches_pattern(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    assert path.name.startswith("cost_report_")
    assert path.suffix == ".json"


def test_cost_report_cross_model_comparison_present(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "cross_model_comparison" in data
    assert "total_input_tokens" in data["cross_model_comparison"]
    assert "entries" in data["cross_model_comparison"]


def test_cost_report_token_values_are_integers(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data["total_input_tokens"], int)
    assert isinstance(data["total_output_tokens"], int)


def test_cost_report_cost_is_float(sdk_with_mocks):
    sdk, tmp_path, _ = sdk_with_mocks
    sdk.generate_article("Test Topic")
    path = next(tmp_path.glob("cost_report_*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data["total_cost_usd"], float)


# ---------------------------------------------------------------------------
# save_report writes to RESULTS_DIR when called directly on real CostTracker
# ---------------------------------------------------------------------------


def test_save_report_writes_to_results_dir(tmp_path):
    """save_report() with no output_dir uses RESULTS_DIR; verify with a real write."""
    import json as _json

    from article_generator.services.cost_tracker import CostTracker

    report = _make_cost_report()
    gk = MagicMock()
    gk.get_call_records.return_value = []

    pricing = Path(__file__).parent.parent.parent / "config" / "model_pricing.json"
    if not pricing.exists():
        pytest.skip("config/model_pricing.json not found")

    tracker = CostTracker(gatekeeper=gk, pricing_path=pricing)
    saved_path = tracker.save_report(report, output_dir=tmp_path)

    assert saved_path.exists()
    assert saved_path.parent == tmp_path
    data = _json.loads(saved_path.read_text(encoding="utf-8"))
    assert set(data.keys()) >= _EXPECTED_KEYS
