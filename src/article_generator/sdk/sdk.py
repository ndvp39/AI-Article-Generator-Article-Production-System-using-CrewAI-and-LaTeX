from __future__ import annotations

import logging
from pathlib import Path

from article_generator.constants import ARTICLE_MD_FILE, RESULTS_DIR
from article_generator.services.crew_service import CrewService
from article_generator.services.file_manager import FileManager
from article_generator.shared.config import ConfigManager
from article_generator.shared.models import ArticleResult

logger = logging.getLogger(__name__)


class ArticleGeneratorSDK:
    """Single entry point for all article generation operations."""

    def __init__(self, config_path: str = "config/setup.json") -> None:
        self._config_manager = ConfigManager(config_dir=Path(config_path).parent)
        self._crew_service = CrewService(config_manager=self._config_manager)
        self._file_manager = FileManager(base_dir=RESULTS_DIR)

    def generate_article(self, topic: str) -> ArticleResult:
        """Run full pipeline: research → write → edit → format → compile."""
        logger.info("generate_article — topic: %s", topic)
        result = self._crew_service.run_pipeline(topic)
        if result.markdown_content:
            self._file_manager.save_markdown(result.markdown_content, ARTICLE_MD_FILE)
        return result

    def compile_pdf(self, tex_path: str) -> object:
        """Compile an existing .tex file to PDF (4-pass LuaLaTeX + biber)."""
        raise NotImplementedError("LaTeXCompiler not yet implemented")

    def get_pipeline_status(self) -> object:
        """Return current stage, agent in progress, and queue depth."""
        raise NotImplementedError("Pipeline status tracking not yet implemented")

    def get_cost_report(self) -> object:
        """Return full token usage breakdown, USD costs, and cross-model comparison."""
        raise NotImplementedError("CostTracker not yet implemented")

    def compare_model_costs(self, models: list[str]) -> object:
        """Project cost of current token usage across given LLM model identifiers."""
        raise NotImplementedError("CostTracker not yet implemented")
