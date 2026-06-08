from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from article_generator.services.tools.search_tools import build_search_tool

# ---------------------------------------------------------------------------
# Auto-skip the whole module when SERPER_API_KEY is absent.
# Load .env first so the key is visible even if not exported in the shell.
# ---------------------------------------------------------------------------

load_dotenv()

if not os.environ.get("SERPER_API_KEY"):
    pytest.skip("SERPER_API_KEY not set — live search tests skipped", allow_module_level=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_build_search_tool_returns_instance():
    tool = build_search_tool()
    assert tool is not None
    assert type(tool).__name__ == "SerperDevTool"


def test_serper_returns_non_empty_string():
    tool = build_search_tool()
    result = tool.run(search_query="artificial intelligence in healthcare")
    assert isinstance(result, str)
    assert len(result) > 50, f"Result too short ({len(result)} chars): {result!r}"


def test_serper_results_contain_relevant_keywords():
    tool = build_search_tool()
    result = tool.run(search_query="machine learning academic research 2024")
    result_lower = result.lower()
    assert any(
        kw in result_lower
        for kw in ["machine", "learning", "research", "model", "ai", "data"]
    ), f"No expected keywords found in result: {result[:200]!r}"


def test_serper_different_queries_return_different_results():
    tool = build_search_tool()
    result_a = tool.run(search_query="quantum computing algorithms")
    result_b = tool.run(search_query="deep learning neural networks")
    assert result_a != result_b, "Different queries should return different results"
