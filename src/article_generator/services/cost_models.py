from __future__ import annotations

from dataclasses import dataclass


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
