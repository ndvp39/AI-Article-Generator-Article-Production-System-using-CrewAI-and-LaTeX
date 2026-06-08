from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

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
# stub methods — raise NotImplementedError (PLAN.md §6.1 signatures verified)
# ---------------------------------------------------------------------------

def test_compile_pdf_raises_not_implemented(mocks):
    with pytest.raises(NotImplementedError):
        ArticleGeneratorSDK().compile_pdf("results/article.tex")


def test_get_pipeline_status_raises_not_implemented(mocks):
    with pytest.raises(NotImplementedError):
        ArticleGeneratorSDK().get_pipeline_status()


def test_get_cost_report_raises_not_implemented(mocks):
    with pytest.raises(NotImplementedError):
        ArticleGeneratorSDK().get_cost_report()


def test_compare_model_costs_raises_not_implemented(mocks):
    with pytest.raises(NotImplementedError):
        ArticleGeneratorSDK().compare_model_costs(["claude-sonnet-4-6", "gemini/gemini-2.0-flash"])
