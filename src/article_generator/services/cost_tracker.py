from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from article_generator.constants import (
    CONFIG_DIR,
    MODEL_PRICING_CONFIG_FILE,
    RESULTS_DIR,
)
from article_generator.shared.gatekeeper import ApiGatekeeper
from article_generator.shared.gatekeeper_models import CallRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CostReport schema — matches PLAN.md §7.12
# ---------------------------------------------------------------------------


@dataclass
class AgentCostEntry:
    """Per-agent token and cost breakdown."""

    agent_name: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class ModelCostEntry:
    """Per-model token and cost summary (used in both by_model and comparison)."""

    model_id: str
    display_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class CrossModelComparison:
    """Project current total token usage onto ≥ 3 different model pricings."""

    total_input_tokens: int
    total_output_tokens: int
    entries: list[ModelCostEntry]


@dataclass
class CostReport:
    """Full cost report emitted after a pipeline run."""

    timestamp: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    budget_alert_threshold_usd: float
    budget_alert_triggered: bool
    by_agent: list[AgentCostEntry]
    by_model: list[ModelCostEntry]
    cross_model_comparison: CrossModelComparison
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class CostTracker:
    """Calculate and report token costs from ApiGatekeeper call records.

    Pricing is loaded once from *pricing_path* (defaults to
    config/model_pricing.json).  Pass an ApiGatekeeper instance so the
    tracker can call get_call_records() without coupling to global state.
    """

    def __init__(
        self,
        gatekeeper: ApiGatekeeper,
        pricing_path: Path | None = None,
        budget_alert_usd: float = 1.0,
    ) -> None:
        self._gatekeeper = gatekeeper
        self._budget_alert_usd = budget_alert_usd
        self._pricing: dict[str, dict] = self._load_pricing(
            pricing_path or CONFIG_DIR / MODEL_PRICING_CONFIG_FILE
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(self) -> CostReport:
        """Aggregate all call records into a full CostReport.

        Side-effect: calls check_budget_alert() and logs a WARNING when
        total cost exceeds the configured threshold.
        """
        records = self._gatekeeper.get_call_records()

        # Aggregate by (agent_name, model)
        by_agent_map: dict[tuple[str, str], AgentCostEntry] = {}
        for rec in records:
            key = (rec.agent_name, rec.model)
            cost = self._cost_for_record(rec)
            if key not in by_agent_map:
                by_agent_map[key] = AgentCostEntry(
                    agent_name=rec.agent_name,
                    model=rec.model,
                    calls=0,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                )
            entry = by_agent_map[key]
            entry.calls += 1
            entry.input_tokens  += rec.input_tokens
            entry.output_tokens += rec.output_tokens
            entry.cost_usd      += cost

        # Aggregate by model
        by_model_map: dict[str, ModelCostEntry] = {}
        for rec in records:
            cost    = self._cost_for_record(rec)
            pricing = self._pricing.get(rec.model, {})
            if rec.model not in by_model_map:
                by_model_map[rec.model] = ModelCostEntry(
                    model_id=rec.model,
                    display_name=pricing.get("display_name", rec.model),
                    provider=pricing.get("provider", "unknown"),
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                )
            m_entry = by_model_map[rec.model]
            m_entry.input_tokens  += rec.input_tokens
            m_entry.output_tokens += rec.output_tokens
            m_entry.cost_usd      += cost

        total_input  = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_cost   = sum(e.cost_usd for e in by_model_map.values())
        total_dur    = sum(r.duration_seconds for r in records)
        alert        = self.check_budget_alert(self._budget_alert_usd)

        # Round per-entry costs
        for e in by_agent_map.values():
            e.cost_usd = round(e.cost_usd, 6)
        for e in by_model_map.values():
            e.cost_usd = round(e.cost_usd, 6)

        cmc = self.compare_models(
            list(self._pricing.keys()),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
        )

        return CostReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_calls=len(records),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost_usd=round(total_cost, 6),
            budget_alert_threshold_usd=self._budget_alert_usd,
            budget_alert_triggered=alert,
            by_agent=sorted(by_agent_map.values(), key=lambda e: e.agent_name),
            by_model=sorted(by_model_map.values(), key=lambda e: e.model_id),
            cross_model_comparison=cmc,
            duration_seconds=round(total_dur, 3),
        )

    def compare_models(
        self,
        models: list[str],
        total_input_tokens: int | None = None,
        total_output_tokens: int | None = None,
    ) -> CrossModelComparison:
        """Project current token totals onto each requested model's pricing.

        If *total_input_tokens* / *total_output_tokens* are not provided
        they are summed from the current call records.  Models absent from
        the pricing table are skipped with a WARNING.
        """
        if total_input_tokens is None or total_output_tokens is None:
            records = self._gatekeeper.get_call_records()
            total_input_tokens  = sum(r.input_tokens  for r in records)
            total_output_tokens = sum(r.output_tokens for r in records)

        entries: list[ModelCostEntry] = []
        for model_id in models:
            pricing = self._pricing.get(model_id)
            if pricing is None:
                logger.warning(
                    "CostTracker: model '%s' not in pricing table — skipping", model_id
                )
                continue
            cost = (
                total_input_tokens  * pricing["input_price_per_mtok"]  / 1_000_000
                + total_output_tokens * pricing["output_price_per_mtok"] / 1_000_000
            )
            entries.append(
                ModelCostEntry(
                    model_id=model_id,
                    display_name=pricing["display_name"],
                    provider=pricing["provider"],
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost_usd=round(cost, 6),
                )
            )

        return CrossModelComparison(
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            entries=entries,
        )

    def check_budget_alert(self, threshold_usd: float) -> bool:
        """Return True if total cost ≥ *threshold_usd*; log WARNING if so."""
        records    = self._gatekeeper.get_call_records()
        total_cost = sum(self._cost_for_record(r) for r in records)
        if total_cost >= threshold_usd:
            logger.warning(
                "CostTracker: budget alert — total cost $%.6f exceeds threshold $%.6f",
                total_cost,
                threshold_usd,
            )
            return True
        return False

    def save_report(
        self,
        report: CostReport,
        output_dir: Path | None = None,
    ) -> Path:
        """Serialise *report* to a timestamped JSON file.

        Writes ``cost_report_<YYYY-MM-DDTHH-MM-SS>.json`` inside
        *output_dir* (defaults to RESULTS_DIR).  Returns the written path.
        """
        if output_dir is None:
            output_dir = RESULTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        dt     = datetime.fromisoformat(report.timestamp)
        ts_str = dt.strftime("%Y-%m-%dT%H-%M-%S")
        path   = output_dir / f"cost_report_{ts_str}.json"

        path.write_text(
            json.dumps(asdict(report), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("CostTracker: saved report → %s", path)
        return path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_pricing(path: Path) -> dict[str, dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["model_pricing"]["models"]

    def _cost_for_record(self, record: CallRecord) -> float:
        pricing = self._pricing.get(record.model)
        if pricing is None:
            return 0.0
        return (
            record.input_tokens  * pricing["input_price_per_mtok"]  / 1_000_000
            + record.output_tokens * pricing["output_price_per_mtok"] / 1_000_000
        )
