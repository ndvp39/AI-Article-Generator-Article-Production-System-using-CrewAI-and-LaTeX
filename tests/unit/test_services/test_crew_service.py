from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from crewai import Process

from article_generator.services.crew_service import CrewService
from article_generator.shared.models import ArticleResult

_BASE = "article_generator.services.crew_service"
_AGENT_KEYS = ("researcher", "writer", "editor", "graph", "latex", "bidi")


def _make_cfg(temperature: str = "0.7") -> MagicMock:
    cfg = MagicMock()
    cfg.load_setup.return_value = {"agents": {"temperature": temperature}}
    return cfg


def _make_crew_output(raw: str = "body", tasks=None) -> MagicMock:
    out = MagicMock()
    out.raw = raw
    out.tasks_output = tasks  # None triggers the `or []` fallback in run_pipeline
    return out


@pytest.fixture()
def mocks():
    with ExitStack() as stack:
        m = {
            "llm": stack.enter_context(patch(f"{_BASE}.build_llm")),
            "tasks": stack.enter_context(patch(f"{_BASE}.build_tasks")),
            "crew": stack.enter_context(patch(f"{_BASE}.Crew")),
            "researcher": stack.enter_context(patch(f"{_BASE}.ResearcherAgent")),
            "writer": stack.enter_context(patch(f"{_BASE}.WriterAgent")),
            "editor": stack.enter_context(patch(f"{_BASE}.EditorAgent")),
            "graph": stack.enter_context(patch(f"{_BASE}.GraphGeneratorAgent")),
            "latex": stack.enter_context(patch(f"{_BASE}.LaTeXFormatterAgent")),
            "bidi": stack.enter_context(patch(f"{_BASE}.BiDiSpecialistAgent")),
        }
        m["crew"].return_value.kickoff.return_value = _make_crew_output()
        yield m


def test_run_pipeline_returns_article_result(mocks):
    result = CrewService(_make_cfg()).run_pipeline("ML")
    assert isinstance(result, ArticleResult)
    assert result.success is True


def test_run_pipeline_uses_temperature_from_config(mocks):
    CrewService(_make_cfg("0.3")).run_pipeline("topic")
    mocks["llm"].assert_called_once_with(temperature=0.3)


def test_run_pipeline_passes_topic_to_build_tasks(mocks):
    CrewService(_make_cfg()).run_pipeline("quantum computing")
    assert mocks["tasks"].call_args.kwargs["topic"] == "quantum computing"


def test_run_pipeline_uses_sequential_process(mocks):
    CrewService(_make_cfg()).run_pipeline("topic")
    assert mocks["crew"].call_args.kwargs["process"] == Process.sequential


def test_run_pipeline_calls_kickoff_once(mocks):
    CrewService(_make_cfg()).run_pipeline("topic")
    mocks["crew"].return_value.kickoff.assert_called_once()


def test_run_pipeline_uses_crew_raw_as_markdown_content(mocks):
    mocks["crew"].return_value.kickoff.return_value = _make_crew_output(raw="article text")
    result = CrewService(_make_cfg()).run_pipeline("topic")
    assert result.markdown_content == "article text"


def test_run_pipeline_maps_task_outputs_to_agent_outputs(mocks):
    task_out = MagicMock()
    task_out.agent = "researcher"
    task_out.description = "Research the topic thoroughly and compile data"
    task_out.raw = "research output"
    mocks["crew"].return_value.kickoff.return_value = _make_crew_output(
        raw="final", tasks=[task_out]
    )
    result = CrewService(_make_cfg()).run_pipeline("topic")
    assert len(result.agent_outputs) == 1
    ao = result.agent_outputs[0]
    assert ao.agent_name == "researcher"
    assert ao.content == "research output"
    assert ao.status == "success"


def test_run_pipeline_none_tasks_output_gives_empty_agent_outputs(mocks):
    mocks["crew"].return_value.kickoff.return_value = _make_crew_output(tasks=None)
    result = CrewService(_make_cfg()).run_pipeline("topic")
    assert result.agent_outputs == []


def test_build_agents_returns_all_six_keys(mocks):
    result = CrewService(_make_cfg())._build_agents(MagicMock())
    assert set(result.keys()) == {
        "researcher", "writer", "editor",
        "graph_generator", "latex_formatter", "bidi_specialist",
    }


def test_build_agents_passes_llm_to_each_builder(mocks):
    llm = MagicMock()
    CrewService(_make_cfg())._build_agents(llm)
    for key in _AGENT_KEYS:
        mocks[key].assert_called_once_with(llm=llm)
        mocks[key].return_value.build.assert_called_once()
