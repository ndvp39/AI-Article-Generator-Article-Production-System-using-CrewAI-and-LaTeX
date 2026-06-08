from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentOutput:
    """Output record for a single agent task in the pipeline."""

    agent_name: str
    task_name: str
    status: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


@dataclass
class ArticleResult:
    """Top-level result returned by CrewService.run_pipeline().

    compilation and cost_report are filled in by ArticleGeneratorSDK
    after the crew run completes (LaTeXCompiler and CostTracker phases).
    """

    success: bool
    markdown_content: str
    tex_path: str
    bib_path: str
    pdf_path: str
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    compilation: object | None = None
    cost_report: object | None = None
