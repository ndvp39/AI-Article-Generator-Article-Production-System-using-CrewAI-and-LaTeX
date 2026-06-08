from __future__ import annotations

import logging

from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent
from article_generator.services.agents.editor import EditorAgent
from article_generator.services.agents.graph_generator import GraphGeneratorAgent
from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent
from article_generator.services.agents.researcher import ResearcherAgent
from article_generator.services.agents.writer import WriterAgent
from article_generator.services.process_orchestrator import ProcessOrchestrator
from article_generator.shared.config import ConfigManager
from article_generator.shared.models import ArticleResult

logger = logging.getLogger(__name__)


class CrewService:
    """Thin facade that delegates the multi-agent pipeline to ProcessOrchestrator."""

    def __init__(self, config_manager: ConfigManager) -> None:
        self._cfg = config_manager

    def run_pipeline(self, topic: str) -> ArticleResult:
        """Load config and delegate entirely to ProcessOrchestrator.run()."""
        setup = self._cfg.load_setup()
        orchestrator = ProcessOrchestrator(config=setup)
        logger.info("CrewService → ProcessOrchestrator — topic: %s", topic)
        return orchestrator.run(topic)

    def _build_agents(self) -> dict[str, type]:
        """Return the 6 agent builder classes (reference map; agents are not instantiated here).

        Instantiation happens inside each OS subprocess via AgentProcessRunner.
        """
        return {
            "researcher":      ResearcherAgent,
            "writer":          WriterAgent,
            "editor":          EditorAgent,
            "graph_generator": GraphGeneratorAgent,
            "latex_formatter": LaTeXFormatterAgent,
            "bidi_specialist": BiDiSpecialistAgent,
        }
