from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.graph_generator import GraphGeneratorAgent

_PATCH_AGENT = "article_generator.services.agents.graph_generator.Agent"
_PATCH_TOOL = "article_generator.services.agents.graph_generator.LocalCodeInterpreterTool"


@pytest.fixture()
def mock_agent_cls():
    with patch(_PATCH_AGENT) as m:
        yield m


@pytest.fixture()
def mock_tool_cls():
    with patch(_PATCH_TOOL) as m:
        yield m


def test_build_returns_crewai_agent(mock_agent_cls, mock_tool_cls):
    result = GraphGeneratorAgent().build()
    assert result is mock_agent_cls.return_value


def test_graph_generator_uses_code_interpreter_tool(mock_agent_cls, mock_tool_cls):
    GraphGeneratorAgent().build()
    mock_tool_cls.assert_called_once()
    kwargs = mock_agent_cls.call_args.kwargs
    assert mock_tool_cls.return_value in kwargs["tools"]


def test_graph_generator_role(mock_agent_cls, mock_tool_cls):
    GraphGeneratorAgent().build()
    assert mock_agent_cls.call_args.kwargs["role"] == "Data Visualization Specialist"


def test_skills_path_contains_graph_generator(mock_agent_cls, mock_tool_cls):
    GraphGeneratorAgent().build()
    skills = mock_agent_cls.call_args.kwargs["skills"]
    assert any("graph_generator" in str(s) for s in skills)


def test_llm_forwarded_when_provided(mock_agent_cls, mock_tool_cls):
    llm = MagicMock()
    GraphGeneratorAgent(llm=llm).build()
    assert mock_agent_cls.call_args.kwargs["llm"] is llm
