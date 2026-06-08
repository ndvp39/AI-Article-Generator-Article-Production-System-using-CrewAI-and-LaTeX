from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.researcher import ResearcherAgent

_PATCH_AGENT = "article_generator.services.agents.researcher.Agent"
_PATCH_TOOL = "article_generator.services.agents.researcher.build_search_tool"


@pytest.fixture()
def mock_agent_cls():
    with patch(_PATCH_AGENT) as m:
        yield m


@pytest.fixture()
def mock_search_tool():
    with patch(_PATCH_TOOL) as m:
        yield m


def test_build_returns_crewai_agent(mock_agent_cls, mock_search_tool):
    result = ResearcherAgent().build()
    assert result is mock_agent_cls.return_value


def test_researcher_uses_search_tool(mock_agent_cls, mock_search_tool):
    ResearcherAgent().build()
    mock_search_tool.assert_called_once()
    kwargs = mock_agent_cls.call_args.kwargs
    assert mock_search_tool.return_value in kwargs["tools"]


def test_researcher_role(mock_agent_cls, mock_search_tool):
    ResearcherAgent().build()
    assert mock_agent_cls.call_args.kwargs["role"] == "Senior Academic Researcher"


def test_skills_path_contains_researcher(mock_agent_cls, mock_search_tool):
    ResearcherAgent().build()
    skills = mock_agent_cls.call_args.kwargs["skills"]
    assert any("researcher" in str(s) for s in skills)


def test_llm_forwarded_when_provided(mock_agent_cls, mock_search_tool):
    llm = MagicMock()
    ResearcherAgent(llm=llm).build()
    assert mock_agent_cls.call_args.kwargs["llm"] is llm


def test_llm_omitted_when_none(mock_agent_cls, mock_search_tool):
    ResearcherAgent(llm=None).build()
    assert "llm" not in mock_agent_cls.call_args.kwargs
