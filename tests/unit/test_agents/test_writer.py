from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.writer import WriterAgent

_PATCH_AGENT = "article_generator.services.agents.writer.Agent"


@pytest.fixture()
def mock_agent_cls():
    with patch(_PATCH_AGENT) as m:
        yield m


def test_build_returns_crewai_agent(mock_agent_cls):
    result = WriterAgent().build()
    assert result is mock_agent_cls.return_value


def test_writer_has_no_tools(mock_agent_cls):
    WriterAgent().build()
    assert mock_agent_cls.call_args.kwargs["tools"] == []


def test_writer_role(mock_agent_cls):
    WriterAgent().build()
    assert mock_agent_cls.call_args.kwargs["role"] == "Academic Article Writer"


def test_skills_path_contains_writer(mock_agent_cls):
    WriterAgent().build()
    skills = mock_agent_cls.call_args.kwargs["skills"]
    assert any("writer" in str(s) for s in skills)


def test_llm_forwarded_when_provided(mock_agent_cls):
    llm = MagicMock()
    WriterAgent(llm=llm).build()
    assert mock_agent_cls.call_args.kwargs["llm"] is llm
