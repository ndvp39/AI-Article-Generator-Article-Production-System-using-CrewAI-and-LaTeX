from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from article_generator.constants import CONFIG_DIR, MODEL_PRICING_CONFIG_FILE, RESULTS_DIR
from article_generator.services.agent_cost_log import load_subprocess_records
from article_generator.services.cost_models import (
    AgentCostEntry,
    CostReport,
    CrossModelComparison,
    ModelCostEntry,
)
from article_generator.shared.gatekeeper import ApiGatekeeper
from article_generator.shared.gatekeeper_models import CallRecord

logger = logging.getLogger(__name__)


class CostTracker:
    """Aggregate call records from ApiGatekeeper; compute USD costs and reports."""

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

    def generate_report(self) -> CostReport:
        """Return a full CostReport aggregated from all current call records."""
        # Merge main-process records (gatekeeper) with subprocess records (agent_costs/).
        records = self._gatekeeper.get_call_records() + load_subprocess_records()
        by_agent: dict[tuple[str, str], AgentCostEntry] = {}
        by_model: dict[str, ModelCostEntry] = {}
        for rec in records:
            cost = self._cost_for_record(rec)
            key = (rec.agent_name, rec.model)
            if key not in by_agent:
                by_agent[key] = AgentCostEntry(
                    agent_name=rec.agent_name, model=rec.model,
                    calls=0, input_tokens=0, output_tokens=0, cost_usd=0.0,
                )
            e = by_agent[key]
            e.calls += 1; e.input_tokens += rec.input_tokens; e.output_tokens += rec.output_tokens; e.cost_usd += cost  # noqa: E702
            pricing = self._pricing.get(rec.model, {})
            if rec.model not in by_model:
                by_model[rec.model] = ModelCostEntry(
                    model_id=rec.model,
                    display_name=pricing.get("display_name", rec.model),
                    provider=pricing.get("provider", "unknown"),
                    input_tokens=0, output_tokens=0, cost_usd=0.0,
                )
            m = by_model[rec.model]
            m.input_tokens += rec.input_tokens; m.output_tokens += rec.output_tokens; m.cost_usd += cost  # noqa: E702
        total_in = sum(r.input_tokens for r in records)
        total_out = sum(r.output_tokens for r in records)
        total_cost = sum(e.cost_usd for e in by_model.values())
        total_dur = sum(r.duration_seconds for r in records)
        alert = self.check_budget_alert(self._budget_alert_usd)
        for e in list(by_agent.values()) + list(by_model.values()):
            e.cost_usd = round(e.cost_usd, 6)
        cmc = self.compare_models(list(self._pricing.keys()), total_in, total_out)
        return CostReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_calls=len(records),
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cost_usd=round(total_cost, 6),
            budget_alert_threshold_usd=self._budget_alert_usd,
            budget_alert_triggered=alert,
            by_agent=sorted(by_agent.values(), key=lambda x: x.agent_name),
            by_model=sorted(by_model.values(), key=lambda x: x.model_id),
            cross_model_comparison=cmc,
            duration_seconds=round(total_dur, 3),
        )

    def compare_models(
        self,
        models: list[str],
        total_input_tokens: int | None = None,
        total_output_tokens: int | None = None,
    ) -> CrossModelComparison:
        """Project token totals onto each model's pricing; return CrossModelComparison."""
        if total_input_tokens is None or total_output_tokens is None:
            recs = self._gatekeeper.get_call_records() + load_subprocess_records()
            total_input_tokens, total_output_tokens = (
                sum(r.input_tokens for r in recs), sum(r.output_tokens for r in recs)
            )
        entries: list[ModelCostEntry] = []
        for model_id in models:
            p = self._pricing.get(model_id)
            if p is None:
                logger.warning("CostTracker: model '%s' not in pricing — skipping", model_id)
                continue
            cost = round(
                (total_input_tokens * p["input_price_per_mtok"]
                 + total_output_tokens * p["output_price_per_mtok"]) / 1_000_000, 6
            )
            entries.append(ModelCostEntry(
                model_id=model_id, display_name=p["display_name"], provider=p["provider"],
                input_tokens=total_input_tokens, output_tokens=total_output_tokens, cost_usd=cost,
            ))
        return CrossModelComparison(
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            entries=entries,
        )

    def check_budget_alert(self, threshold_usd: float) -> bool:
        """Return True if total cost ≥ threshold_usd; log WARNING if so."""
        all_records = self._gatekeeper.get_call_records() + load_subprocess_records()
        total = sum(self._cost_for_record(r) for r in all_records)
        if total >= threshold_usd:
            logger.warning(
                "CostTracker: budget alert — $%.6f exceeds $%.6f", total, threshold_usd,
            )
            return True
        return False

    def save_report(self, report: CostReport, output_dir: Path | None = None) -> Path:
        """Serialise report to a timestamped JSON file; return path written."""
        output_dir = output_dir or RESULTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        dt = datetime.fromisoformat(report.timestamp)
        path = output_dir / f"cost_report_{dt.strftime('%Y-%m-%dT%H-%M-%S')}.json"
        path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("CostTracker: saved report → %s", path)
        return path

    @staticmethod
    def _load_pricing(path: Path) -> dict[str, dict]:
        return json.loads(path.read_text(encoding="utf-8"))["model_pricing"]["models"]

    def _cost_for_record(self, record: CallRecord) -> float:
        p = self._pricing.get(record.model)
        if p is None:
            return 0.0
        return (record.input_tokens * p["input_price_per_mtok"]
                + record.output_tokens * p["output_price_per_mtok"]) / 1_000_000
