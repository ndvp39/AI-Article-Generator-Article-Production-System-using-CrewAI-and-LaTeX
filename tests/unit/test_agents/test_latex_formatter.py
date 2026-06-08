from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent

_PATCH_AGENT = "article_generator.services.agents.latex_formatter.Agent"
_PATCH_TOOL = "article_generator.services.agents.latex_formatter.FileWriterTool"


@pytest.fixture()
def mock_agent_cls():
    with patch(_PATCH_AGENT) as m:
        yield m


@pytest.fixture()
def mock_tool_cls():
    with patch(_PATCH_TOOL) as m:
        yield m


def test_build_returns_crewai_agent(mock_agent_cls, mock_tool_cls):
    result = LaTeXFormatterAgent().build()
    assert result is mock_agent_cls.return_value


def test_latex_uses_file_writer_tool(mock_agent_cls, mock_tool_cls):
    LaTeXFormatterAgent().build()
    mock_tool_cls.assert_called_once()
    kwargs = mock_agent_cls.call_args.kwargs
    assert mock_tool_cls.return_value in kwargs["tools"]


def test_latex_formatter_role(mock_agent_cls, mock_tool_cls):
    LaTeXFormatterAgent().build()
    assert mock_agent_cls.call_args.kwargs["role"] == "LaTeX Typesetting Specialist"


def test_skills_path_contains_latex_formatter(mock_agent_cls, mock_tool_cls):
    LaTeXFormatterAgent().build()
    skills = mock_agent_cls.call_args.kwargs["skills"]
    assert any("latex_formatter" in str(s) for s in skills)


def test_llm_forwarded_when_provided(mock_agent_cls, mock_tool_cls):
    llm = MagicMock()
    LaTeXFormatterAgent(llm=llm).build()
    assert mock_agent_cls.call_args.kwargs["llm"] is llm
