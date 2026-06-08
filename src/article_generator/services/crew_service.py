from __future__ import annotations

import logging

from crewai import Crew, Process

from article_generator.constants import (
    ARTICLE_PDF_FILE,
    ARTICLE_TEX_FILE,
    REFERENCES_BIB_FILE,
    RESULTS_DIR,
)
from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent
from article_generator.services.agents.editor import EditorAgent
from article_generator.services.agents.graph_generator import GraphGeneratorAgent
from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent
from article_generator.services.agents.researcher import ResearcherAgent
from article_generator.services.agents.writer import WriterAgent
from article_generator.services.tasks.task_definitions import build_tasks
from article_generator.shared.config import ConfigManager
from article_generator.shared.llm_factory import build_llm
from article_generator.shared.models import AgentOutput, ArticleResult

logger = logging.getLogger(__name__)


class CrewService:
    """Assembles and runs the 6-agent CrewAI pipeline."""

    def __init__(self, config_manager: ConfigManager) -> None:
        self._cfg = config_manager

    def run_pipeline(self, topic: str) -> ArticleResult:
        """Build agents + tasks, kick off the crew, return ArticleResult."""
        setup = self._cfg.load_setup()
        temperature = float(setup["agents"]["temperature"])
        llm = build_llm(temperature=temperature)

        agents = self._build_agents(llm)
        tasks = build_tasks(
            researcher=agents["researcher"],
            writer=agents["writer"],
            editor=agents["editor"],
            graph_generator=agents["graph_generator"],
            latex_formatter=agents["latex_formatter"],
            bidi_specialist=agents["bidi_specialist"],
            topic=topic,
        )

        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        logger.info("CrewAI pipeline starting — topic: %s", topic)
        crew_output = crew.kickoff()
        logger.info("CrewAI pipeline complete")

        agent_outputs = [
            AgentOutput(
                agent_name=t.agent or "unknown",
                task_name=(t.description or "")[:50],
                status="success",
                content=t.raw or "",
            )
            for t in (crew_output.tasks_output or [])
        ]

        return ArticleResult(
            success=True,
            markdown_content=crew_output.raw or "",
            tex_path=str(RESULTS_DIR / ARTICLE_TEX_FILE),
            bib_path=str(RESULTS_DIR / REFERENCES_BIB_FILE),
            pdf_path=str(RESULTS_DIR / ARTICLE_PDF_FILE),
            agent_outputs=agent_outputs,
        )

    def _build_agents(self, llm: object) -> dict:
        """Instantiate all 6 agents with the active LLM."""
        return {
            "researcher": ResearcherAgent(llm=llm).build(),
            "writer": WriterAgent(llm=llm).build(),
            "editor": EditorAgent(llm=llm).build(),
            "graph_generator": GraphGeneratorAgent(llm=llm).build(),
            "latex_formatter": LaTeXFormatterAgent(llm=llm).build(),
            "bidi_specialist": BiDiSpecialistAgent(llm=llm).build(),
        }
