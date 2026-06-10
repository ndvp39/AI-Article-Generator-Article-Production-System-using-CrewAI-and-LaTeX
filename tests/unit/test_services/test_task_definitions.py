from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

_BASE = "article_generator.services.tasks.task_definitions"


def _make_agent(name: str = "agent") -> MagicMock:
    a = MagicMock()
    a.role = name
    return a


@pytest.fixture()
def mock_task_cls():
    with patch(f"{_BASE}.Task") as MockTask:
        MockTask.side_effect = lambda **kw: MagicMock(**kw)
        yield MockTask


# ---------------------------------------------------------------------------
# String constants — always accessible without mocking
# ---------------------------------------------------------------------------


def test_research_desc_contains_topic_placeholder():
    from article_generator.services.tasks.task_definitions import _RESEARCH_DESC
    assert "{topic}" in _RESEARCH_DESC


def test_write_desc_contains_topic_placeholder():
    from article_generator.services.tasks.task_definitions import _WRITE_DESC
    assert "{topic}" in _WRITE_DESC


def test_write_desc_requires_hebrew_language():
    from article_generator.services.tasks.task_definitions import _WRITE_DESC
    assert "Hebrew" in _WRITE_DESC


def test_write_desc_requires_minimum_word_count():
    from article_generator.services.tasks.task_definitions import _WRITE_DESC
    assert "12,000" in _WRITE_DESC


def test_latex_desc_requires_xelatex_and_hebrew_main():
    from article_generator.services.tasks.task_definitions import _LATEX_DESC
    assert "XeLaTeX" in _LATEX_DESC or "xelatex" in _LATEX_DESC.lower()
    assert "setmainlanguage{hebrew}" in _LATEX_DESC


def test_bidi_desc_requires_confirmation_only_output():
    from article_generator.services.tasks.task_definitions import _BIDI_DESC
    assert "FileReadTool" in _BIDI_DESC or "FileWriterTool" in _BIDI_DESC


def test_review_desc_does_not_require_topic():
    from article_generator.services.tasks.task_definitions import _REVIEW_DESC
    assert isinstance(_REVIEW_DESC, str) and len(_REVIEW_DESC) > 0


def test_all_output_strings_are_non_empty():
    from article_generator.services.tasks.task_definitions import (
        _BIDI_OUT,
        _GRAPH_OUT,
        _LATEX_OUT,
        _RESEARCH_OUT,
        _REVIEW_OUT,
        _WRITE_OUT,
    )
    for s in [_RESEARCH_OUT, _WRITE_OUT, _REVIEW_OUT, _GRAPH_OUT, _LATEX_OUT, _BIDI_OUT]:
        assert isinstance(s, str) and len(s) > 0


# ---------------------------------------------------------------------------
# build_tasks
# ---------------------------------------------------------------------------


def test_build_tasks_returns_six_tasks(mock_task_cls):
    from article_generator.services.tasks.task_definitions import build_tasks
    tasks = build_tasks(
        researcher=_make_agent("researcher"),
        writer=_make_agent("writer"),
        editor=_make_agent("editor"),
        graph_generator=_make_agent("graph_gen"),
        latex_formatter=_make_agent("latex"),
        bidi_specialist=_make_agent("bidi"),
        topic="Neural Networks",
    )
    assert len(tasks) == 6


def test_build_tasks_calls_task_six_times(mock_task_cls):
    from article_generator.services.tasks.task_definitions import build_tasks
    build_tasks(
        researcher=_make_agent(),
        writer=_make_agent(),
        editor=_make_agent(),
        graph_generator=_make_agent(),
        latex_formatter=_make_agent(),
        bidi_specialist=_make_agent(),
        topic="AI",
    )
    assert mock_task_cls.call_count == 6


def test_build_tasks_research_description_has_topic(mock_task_cls):
    from article_generator.services.tasks.task_definitions import build_tasks
    build_tasks(
        researcher=_make_agent(),
        writer=_make_agent(),
        editor=_make_agent(),
        graph_generator=_make_agent(),
        latex_formatter=_make_agent(),
        bidi_specialist=_make_agent(),
        topic="Quantum Computing",
    )
    first_call_desc = mock_task_cls.call_args_list[0].kwargs["description"]
    assert "Quantum Computing" in first_call_desc


def test_build_tasks_assigns_correct_agents(mock_task_cls):
    from article_generator.services.tasks.task_definitions import build_tasks
    researcher = _make_agent("researcher")
    writer = _make_agent("writer")
    build_tasks(
        researcher=researcher,
        writer=writer,
        editor=_make_agent(),
        graph_generator=_make_agent(),
        latex_formatter=_make_agent(),
        bidi_specialist=_make_agent(),
        topic="ML",
    )
    assert mock_task_cls.call_args_list[0].kwargs["agent"] is researcher
    assert mock_task_cls.call_args_list[1].kwargs["agent"] is writer


def test_build_tasks_write_task_has_context(mock_task_cls):
    from article_generator.services.tasks.task_definitions import build_tasks
    build_tasks(
        researcher=_make_agent(),
        writer=_make_agent(),
        editor=_make_agent(),
        graph_generator=_make_agent(),
        latex_formatter=_make_agent(),
        bidi_specialist=_make_agent(),
        topic="NLP",
    )
    write_call = mock_task_cls.call_args_list[1]
    assert "context" in write_call.kwargs
    assert len(write_call.kwargs["context"]) == 1
