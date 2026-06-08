from __future__ import annotations

# Integration test: process isolation
#
# Verifies that each AgentProcessRunner spawns a REAL OS subprocess with a
# distinct PID that differs from the parent process and from every other agent.
#
# No LLM or Serper calls are made: each subprocess blocks on in_queue.get()
# (waiting for its first message) and is terminated before it reaches any
# crewai imports.  No API keys are required.
import os
from multiprocessing import Queue

import pytest

from article_generator.constants import AGENT_TIMEOUT_SECONDS, DEFAULT_AGENT_TIMEOUT_SECONDS
from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent
from article_generator.services.agents.editor import EditorAgent
from article_generator.services.agents.graph_generator import GraphGeneratorAgent
from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent
from article_generator.services.agents.researcher import ResearcherAgent
from article_generator.services.agents.writer import WriterAgent
from article_generator.services.tasks.task_definitions import (
    _BIDI_DESC,
    _BIDI_OUT,
    _GRAPH_DESC,
    _GRAPH_OUT,
    _LATEX_DESC,
    _LATEX_OUT,
    _RESEARCH_DESC,
    _RESEARCH_OUT,
    _REVIEW_DESC,
    _REVIEW_OUT,
    _WRITE_DESC,
    _WRITE_OUT,
)
from article_generator.shared.process_runner import AgentProcessRunner

_AGENT_SPECS: list[tuple[type, str, str, str]] = [
    (ResearcherAgent,     _RESEARCH_DESC, _RESEARCH_OUT, "researcher"),
    (WriterAgent,         _WRITE_DESC,    _WRITE_OUT,    "writer"),
    (EditorAgent,         _REVIEW_DESC,   _REVIEW_OUT,   "editor"),
    (GraphGeneratorAgent, _GRAPH_DESC,    _GRAPH_OUT,    "graph_generator"),
    (LaTeXFormatterAgent, _LATEX_DESC,    _LATEX_OUT,    "latex_formatter"),
    (BiDiSpecialistAgent, _BIDI_DESC,     _BIDI_OUT,     "bidi_specialist"),
]


# ---------------------------------------------------------------------------
# Module-scoped fixture: start 6 real subprocesses, clean up after all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def started_runners() -> list[AgentProcessRunner]:
    """Spawn 6 AgentProcessRunners; terminate them all after the module runs."""
    runners: list[AgentProcessRunner] = []
    try:
        for agent_cls, task_desc, expected_out, agent_name in _AGENT_SPECS:
            in_q: Queue = Queue()
            out_q: Queue = Queue()
            runner = AgentProcessRunner(
                agent_cls=agent_cls,
                task_description=task_desc,
                expected_output=expected_out,
                in_queue=in_q,
                out_queue=out_q,
                agent_name=agent_name,
                timeout=AGENT_TIMEOUT_SECONDS.get(agent_name, DEFAULT_AGENT_TIMEOUT_SECONDS),
                llm_kwargs={"temperature": 0.7},
            )
            runner.start()
            runners.append(runner)
        yield runners
    finally:
        for runner in runners:
            if runner.is_alive():
                runner.terminate()
            runner.join(timeout=5.0)


# ---------------------------------------------------------------------------
# Isolation assertions
# ---------------------------------------------------------------------------

def test_six_processes_spawned(started_runners):
    assert len(started_runners) == 6


def test_all_pids_are_non_none(started_runners):
    for runner in started_runners:
        assert runner.pid is not None, f"Agent '{runner.agent_name}' has no PID after start()"


def test_all_pids_differ_from_parent_process(started_runners):
    parent = os.getpid()
    for runner in started_runners:
        assert runner.pid != parent, (
            f"Agent '{runner.agent_name}' shares PID {runner.pid} with the parent process"
        )


def test_all_six_pids_are_distinct(started_runners):
    pids = [runner.pid for runner in started_runners]
    assert len(set(pids)) == 6, (
        f"Expected 6 distinct PIDs but got duplicates: {pids}"
    )


def test_all_processes_are_alive_while_waiting(started_runners):
    """Subprocesses block on in_queue.get — they must still be running."""
    for runner in started_runners:
        assert runner.is_alive(), f"Agent '{runner.agent_name}' (pid={runner.pid}) is not alive"


def test_agent_names_in_pipeline_order(started_runners):
    names = [r.agent_name for r in started_runners]
    assert names == [
        "researcher", "writer", "editor",
        "graph_generator", "latex_formatter", "bidi_specialist",
    ]
