from __future__ import annotations

import os
import re

import pytest
from dotenv import load_dotenv

from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.shared.models import ArticleResult

# ---------------------------------------------------------------------------
# Skip the whole module unless both API keys are present.
# ---------------------------------------------------------------------------

load_dotenv()

_has_llm = bool(os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY"))
_has_serper = bool(os.environ.get("SERPER_API_KEY"))

if not (_has_llm and _has_serper):
    pytest.skip(
        "LLM_API_KEY/GEMINI_API_KEY and SERPER_API_KEY required — full pipeline test skipped",
        allow_module_level=True,
    )

_TOPIC = "The Role of Artificial Intelligence in Modern Healthcare"

# ---------------------------------------------------------------------------
# Run the pipeline once for all tests in this module.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def result() -> ArticleResult:
    return ArticleGeneratorSDK().generate_article(topic=_TOPIC)


# ---------------------------------------------------------------------------
# Structural assertions
# ---------------------------------------------------------------------------

def test_pipeline_reports_success(result):
    assert result.success is True


def test_markdown_content_is_substantial(result):
    assert result.markdown_content
    assert len(result.markdown_content) > 1000, (
        f"Markdown too short: {len(result.markdown_content)} chars"
    )


def test_markdown_contains_abstract(result):
    assert re.search(r"abstract", result.markdown_content, re.IGNORECASE), (
        "Section 'Abstract' not found in output"
    )


def test_markdown_contains_introduction(result):
    assert re.search(r"introduction", result.markdown_content, re.IGNORECASE), (
        "Section 'Introduction' not found in output"
    )


def test_markdown_contains_conclusion(result):
    assert re.search(r"conclusion", result.markdown_content, re.IGNORECASE), (
        "Section 'Conclusion' not found in output"
    )


def test_markdown_contains_references_or_bibliography(result):
    assert re.search(
        r"(references|bibliography)", result.markdown_content, re.IGNORECASE
    ), "Section 'References'/'Bibliography' not found in output"


def test_markdown_has_at_least_four_body_chapters(result):
    content = result.markdown_content
    all_headings = re.findall(r"^#{1,2}\s+.+", content, re.MULTILINE)
    _structural = re.compile(
        r"(abstract|introduction|conclusion|references|bibliography)", re.IGNORECASE
    )
    chapters = [h for h in all_headings if not _structural.search(h)]
    assert len(chapters) >= 4, (
        f"Expected ≥ 4 body chapters, found {len(chapters)}: {chapters}"
    )


def test_result_output_paths_are_set(result):
    assert result.tex_path
    assert result.bib_path
    assert result.pdf_path


def test_agent_outputs_list_is_present(result):
    assert isinstance(result.agent_outputs, list)
