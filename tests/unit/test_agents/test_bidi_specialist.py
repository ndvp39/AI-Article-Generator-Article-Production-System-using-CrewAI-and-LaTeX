from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent

_PATCH_AGENT = "article_generator.services.agents.bidi_specialist.Agent"
_PATCH_READ = "article_generator.services.agents.bidi_specialist.FileReadTool"
_PATCH_WRITE = "article_generator.services.agents.bidi_specialist.FileWriterTool"


@pytest.fixture()
def mock_agent_cls():
    with patch(_PATCH_AGENT) as m:
        yield m


@pytest.fixture()
def mock_read_cls():
    with patch(_PATCH_READ) as m:
        yield m


@pytest.fixture()
def mock_write_cls():
    with patch(_PATCH_WRITE) as m:
        yield m


def test_build_returns_crewai_agent(mock_agent_cls, mock_read_cls, mock_write_cls):
    result = BiDiSpecialistAgent().build()
    assert result is mock_agent_cls.return_value


def test_bidi_has_two_tools(mock_agent_cls, mock_read_cls, mock_write_cls):
    BiDiSpecialistAgent().build()
    assert len(mock_agent_cls.call_args.kwargs["tools"]) == 2


def test_bidi_uses_file_read_and_writer_tools(mock_agent_cls, mock_read_cls, mock_write_cls):
    BiDiSpecialistAgent().build()
    tools = mock_agent_cls.call_args.kwargs["tools"]
    assert mock_read_cls.return_value in tools
    assert mock_write_cls.return_value in tools


def test_bidi_specialist_role(mock_agent_cls, mock_read_cls, mock_write_cls):
    BiDiSpecialistAgent().build()
    assert mock_agent_cls.call_args.kwargs["role"] == "Hebrew–English Bidirectional Text Specialist"


def test_skills_path_contains_bidi_specialist(mock_agent_cls, mock_read_cls, mock_write_cls):
    BiDiSpecialistAgent().build()
    skills = mock_agent_cls.call_args.kwargs["skills"]
    assert any("bidi_specialist" in str(s) for s in skills)


def test_llm_forwarded_when_provided(mock_agent_cls, mock_read_cls, mock_write_cls):
    llm = MagicMock()
    BiDiSpecialistAgent(llm=llm).build()
    assert mock_agent_cls.call_args.kwargs["llm"] is llm
