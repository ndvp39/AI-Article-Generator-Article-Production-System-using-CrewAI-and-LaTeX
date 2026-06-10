from __future__ import annotations

import logging
import os
from pathlib import Path

from article_generator.constants import (
    ARTICLE_MD_FILE,
    ARTICLE_TEX_FILE,
    DEFAULT_LLM_TIER,
    LLM_PROVIDER_CLAUDE,
    REFERENCES_BIB_FILE,
    RESULTS_DIR,
)
from article_generator.services.cost_tracker import CostReport, CostTracker, CrossModelComparison
from article_generator.services.crew_service import CrewService
from article_generator.services.file_manager import FileManager
from article_generator.services.latex_compiler import CompilationResult, LaTeXCompiler
from article_generator.shared.config import ConfigManager
from article_generator.shared.gatekeeper import ApiGatekeeper
from article_generator.shared.models import ArticleResult

logger = logging.getLogger(__name__)


class ArticleGeneratorSDK:
    """Single entry point for all article generation operations."""

    def __init__(self, config_path: str = "config/setup.json") -> None:
        self._config_manager = ConfigManager(config_dir=Path(config_path).parent)
        self._crew_service = CrewService(config_manager=self._config_manager)
        self._file_manager = FileManager(base_dir=RESULTS_DIR)
        provider = os.environ.get("ACTIVE_LLM", LLM_PROVIDER_CLAUDE).lower()
        tier = os.environ.get("LLM_TIER", DEFAULT_LLM_TIER).lower()
        limits = self._config_manager.load_provider_limits(provider, tier)
        self._gatekeeper = ApiGatekeeper(limits)
        self._cost_tracker = CostTracker(gatekeeper=self._gatekeeper)

    def generate_article(self, topic: str) -> ArticleResult:
        """Run full pipeline: research → write → edit → format → compile."""
        logger.info("generate_article — topic: %s", topic)
        result = self._crew_service.run_pipeline(topic)
        if result.markdown_content:
            self._file_manager.save_markdown(result.markdown_content, ARTICLE_MD_FILE)

        # Auto-compile PDF if article.tex was written to disk by the agents.
        tex_path = RESULTS_DIR / ARTICLE_TEX_FILE
        bib_path = RESULTS_DIR / REFERENCES_BIB_FILE
        if tex_path.exists():
            logger.info("generate_article — auto-compiling PDF from %s", tex_path)
            try:
                compilation = self.compile_pdf(str(tex_path), str(bib_path))
                if compilation.success:
                    logger.info(
                        "generate_article — PDF compiled: %s", compilation.pdf_path
                    )
                    result.pdf_path = str(compilation.pdf_path)
                else:
                    logger.warning(
                        "generate_article — PDF compilation failed: %s",
                        compilation.errors,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("generate_article — PDF compilation error: %s", exc)
        else:
            logger.warning(
                "generate_article — %s not found; skipping PDF compilation", tex_path
            )

        report = self._cost_tracker.generate_report()
        self._cost_tracker.save_report(report)
        return result

    def compile_pdf(self, tex_path: str, bib_path: str) -> CompilationResult:
        """Compile an existing .tex file to PDF (4-pass XeLaTeX + biber)."""
        logger.info("compile_pdf — tex: %s, bib: %s", tex_path, bib_path)
        return LaTeXCompiler().compile(tex_path, bib_path)

    def get_pipeline_status(self) -> object:
        """Return current stage, agent in progress, and queue depth."""
        raise NotImplementedError("Pipeline status tracking not yet implemented")

    def get_cost_report(self) -> CostReport:
        """Return full token usage breakdown, USD costs, and cross-model comparison."""
        logger.info("get_cost_report called")
        return self._cost_tracker.generate_report()

    def compare_model_costs(self, models: list[str]) -> CrossModelComparison:
        """Project cost of current token usage across given LLM model identifiers."""
        logger.info("compare_model_costs — models: %s", models)
        return self._cost_tracker.compare_models(models)
