from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.shared.models import ArticleResult

_BASE = "article_generator.sdk.sdk"


def _make_result(markdown: str = "# Article") -> ArticleResult:
    return ArticleResult(
        success=True,
        markdown_content=markdown,
        tex_path="results/article.tex",
        bib_path="results/references.bib",
        pdf_path="results/article.pdf",
    )


@pytest.fixture()
def mocks():
    with ExitStack() as stack:
        m = {
            "config": stack.enter_context(patch(f"{_BASE}.ConfigManager")),
            "crew": stack.enter_context(patch(f"{_BASE}.CrewService")),
            "files": stack.enter_context(patch(f"{_BASE}.FileManager")),
            "gatekeeper": stack.enter_context(patch(f"{_BASE}.ApiGatekeeper")),
            "cost_tracker": stack.enter_context(patch(f"{_BASE}.CostTracker")),
        }
        m["crew"].return_value.run_pipeline.return_value = _make_result()
        yield m


# ---------------------------------------------------------------------------
# __init__ — service wiring
# ---------------------------------------------------------------------------

def test_init_creates_config_manager_from_config_path(mocks):
    ArticleGeneratorSDK(config_path="config/setup.json")
    mocks["config"].assert_called_once_with(config_dir=Path("config"))


def test_init_uses_custom_config_path(mocks):
    ArticleGeneratorSDK(config_path="custom/path/setup.json")
    mocks["config"].assert_called_once_with(config_dir=Path("custom/path"))


def test_init_passes_config_manager_to_crew_service(mocks):
    ArticleGeneratorSDK()
    mocks["crew"].assert_called_once_with(config_manager=mocks["config"].return_value)


# ---------------------------------------------------------------------------
# generate_article — delegation and behaviour
# ---------------------------------------------------------------------------

def test_generate_article_delegates_topic_to_crew(mocks):
    ArticleGeneratorSDK().generate_article("AI in Medicine")
    mocks["crew"].return_value.run_pipeline.assert_called_once_with("AI in Medicine")


def test_generate_article_returns_article_result(mocks):
    result = ArticleGeneratorSDK().generate_article("topic")
    assert isinstance(result, ArticleResult)
    assert result.success is True


def test_generate_article_saves_markdown_when_content_present(mocks):
    mocks["crew"].return_value.run_pipeline.return_value = _make_result(markdown="# Hello")
    ArticleGeneratorSDK().generate_article("topic")
    mocks["files"].return_value.save_markdown.assert_called_once()


def test_generate_article_skips_save_when_markdown_is_empty(mocks):
    mocks["crew"].return_value.run_pipeline.return_value = _make_result(markdown="")
    ArticleGeneratorSDK().generate_article("topic")
    mocks["files"].return_value.save_markdown.assert_not_called()


# ---------------------------------------------------------------------------
# compile_pdf — delegation to LaTeXCompiler
# ---------------------------------------------------------------------------


def test_compile_pdf_instantiates_latex_compiler(mocks):
    """compile_pdf() must create a LaTeXCompiler instance and delegate."""
    with patch(f"{_BASE}.LaTeXCompiler") as mock_cls:
        mock_cls.return_value.compile.return_value = MagicMock()
        ArticleGeneratorSDK().compile_pdf("results/article.tex", "results/references.bib")
    mock_cls.assert_called_once_with()


def test_compile_pdf_passes_both_paths_to_compile(mocks):
    with patch(f"{_BASE}.LaTeXCompiler") as mock_cls:
        mock_cls.return_value.compile.return_value = MagicMock()
        ArticleGeneratorSDK().compile_pdf("results/article.tex", "results/references.bib")
    mock_cls.return_value.compile.assert_called_once_with(
        "results/article.tex", "results/references.bib"
    )


def test_compile_pdf_returns_compilation_result(mocks):
    expected = MagicMock()
    with patch(f"{_BASE}.LaTeXCompiler") as mock_cls:
        mock_cls.return_value.compile.return_value = expected
        result = ArticleGeneratorSDK().compile_pdf(
            "results/article.tex", "results/references.bib"
        )
    assert result is expected


# ---------------------------------------------------------------------------
# remaining stubs — still raise NotImplementedError
# ---------------------------------------------------------------------------


def test_get_pipeline_status_raises_not_implemented(mocks):
    with pytest.raises(NotImplementedError):
        ArticleGeneratorSDK().get_pipeline_status()


# ---------------------------------------------------------------------------
# get_cost_report — delegates to CostTracker.generate_report
# ---------------------------------------------------------------------------


def test_get_cost_report_calls_generate_report(mocks):
    ArticleGeneratorSDK().get_cost_report()
    mocks["cost_tracker"].return_value.generate_report.assert_called_once_with()


def test_get_cost_report_returns_generate_report_result(mocks):
    expected = MagicMock()
    mocks["cost_tracker"].return_value.generate_report.return_value = expected
    result = ArticleGeneratorSDK().get_cost_report()
    assert result is expected


# ---------------------------------------------------------------------------
# compare_model_costs — delegates to CostTracker.compare_models
# ---------------------------------------------------------------------------


def test_compare_model_costs_calls_compare_models(mocks):
    models = ["claude-sonnet-4-6", "gpt-4o", "gemini-2.0-flash"]
    ArticleGeneratorSDK().compare_model_costs(models)
    mocks["cost_tracker"].return_value.compare_models.assert_called_once_with(models)


def test_compare_model_costs_returns_compare_models_result(mocks):
    expected = MagicMock()
    mocks["cost_tracker"].return_value.compare_models.return_value = expected
    result = ArticleGeneratorSDK().compare_model_costs(["claude-sonnet-4-6"])
    assert result is expected


# ---------------------------------------------------------------------------
# __init__ — CostTracker wiring
# ---------------------------------------------------------------------------


def test_init_creates_gatekeeper_with_provider_limits(mocks):
    ArticleGeneratorSDK()
    provider_limits = mocks["config"].return_value.load_provider_limits.return_value
    mocks["gatekeeper"].assert_called_once_with(provider_limits)


def test_init_passes_gatekeeper_to_cost_tracker(mocks):
    ArticleGeneratorSDK()
    mocks["cost_tracker"].assert_called_once_with(
        gatekeeper=mocks["gatekeeper"].return_value
    )
