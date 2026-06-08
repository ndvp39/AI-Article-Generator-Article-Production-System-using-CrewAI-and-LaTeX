from __future__ import annotations

# Integration test: IPC message passing end-to-end
#
# Verifies that a message injected at the researcher's input queue travels
# through all 6 pipeline stages and arrives correctly formatted at the
# bidi specialist's output queue.
#
# Strategy: each subprocess is a simple stub that reads one AgentMessage from
# its in_queue and writes one AgentMessage to its out_queue — no LLM, no Serper.
# The GatekeeperRouter validates and routes every hop using real Queues.
# No API keys required.
from dataclasses import dataclass
from multiprocessing import Process, Queue

import pytest

from article_generator.services.gatekeeper_router import GatekeeperRouter
from article_generator.shared.ipc_models import AgentMessage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AGENT_NAMES = [
    "researcher",
    "writer",
    "editor",
    "graph_generator",
    "latex_formatter",
    "bidi_specialist",
]
_N_AGENTS = len(_AGENT_NAMES)
_INITIAL_TOPIC = "integration-test-topic"
_INITIAL_CONTENT = "start"
_TIMEOUT = 30  # seconds each subprocess may block waiting for its input


# ---------------------------------------------------------------------------
# Stub subprocess — module-level so it is picklable on Windows (spawn)
# ---------------------------------------------------------------------------

def _stub_agent(in_queue: Queue, out_queue: Queue, agent_name: str) -> None:
    """Minimal subprocess: consume one input message, emit one output message."""
    in_msg: AgentMessage = in_queue.get(timeout=_TIMEOUT)
    out_queue.put(
        AgentMessage(
            sender=agent_name,
            recipient="",           # GatekeeperRouter fills the recipient
            content=f"output-from-{agent_name}",
            topic=in_msg.topic,
            message_type="output",
        )
    )


# ---------------------------------------------------------------------------
# Pipeline result dataclass
# ---------------------------------------------------------------------------

@dataclass
class _PipelineRun:
    final_msg: AgentMessage
    processes: list[Process]
    router: GatekeeperRouter


# ---------------------------------------------------------------------------
# Module-scoped fixture: run the full stub pipeline once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_run() -> _PipelineRun:
    """Spawn 6 stub processes + GatekeeperRouter; inject initial message;
    collect final output; tear down everything after all tests in this module."""
    pipeline: list[tuple[Queue, Queue]] = [(Queue(), Queue()) for _ in range(_N_AGENTS)]

    processes = [
        Process(
            target=_stub_agent,
            args=(pipeline[i][0], pipeline[i][1], _AGENT_NAMES[i]),
            name=f"stub-{_AGENT_NAMES[i]}",
            daemon=False,
        )
        for i in range(_N_AGENTS)
    ]

    router = GatekeeperRouter(pipeline=pipeline, agent_names=_AGENT_NAMES)

    for proc in processes:
        proc.start()

    router.start()

    # Inject the initial message into the researcher's input queue
    pipeline[0][0].put(
        AgentMessage(
            sender="orchestrator",
            recipient="researcher",
            content=_INITIAL_CONTENT,
            topic=_INITIAL_TOPIC,
            message_type="input",
        )
    )

    try:
        final_msg: AgentMessage = pipeline[_N_AGENTS - 1][1].get(timeout=_TIMEOUT)
    finally:
        router.stop()
        for proc in processes:
            proc.join(timeout=10.0)
            if proc.is_alive():
                proc.terminate()

    return _PipelineRun(final_msg=final_msg, processes=processes, router=router)


# ---------------------------------------------------------------------------
# Final message assertions
# ---------------------------------------------------------------------------

def test_final_message_arrives(pipeline_run):
    assert pipeline_run.final_msg is not None


def test_final_sender_is_bidi_specialist(pipeline_run):
    assert pipeline_run.final_msg.sender == "bidi_specialist"


def test_final_message_type_is_output(pipeline_run):
    assert pipeline_run.final_msg.message_type == "output"


def test_topic_preserved_end_to_end(pipeline_run):
    assert pipeline_run.final_msg.topic == _INITIAL_TOPIC


def test_final_content_is_non_empty(pipeline_run):
    assert pipeline_run.final_msg.content.strip()


def test_final_content_identifies_bidi_specialist(pipeline_run):
    assert "bidi_specialist" in pipeline_run.final_msg.content


# ---------------------------------------------------------------------------
# Router health assertions
# ---------------------------------------------------------------------------

def test_gatekeeper_router_reports_no_error(pipeline_run):
    assert pipeline_run.router.last_error is None


# ---------------------------------------------------------------------------
# Process exit assertions
# ---------------------------------------------------------------------------

def test_all_stub_processes_exited_cleanly(pipeline_run):
    for proc in pipeline_run.processes:
        assert proc.exitcode == 0, (
            f"Process '{proc.name}' exited with code {proc.exitcode}"
        )


def test_all_stub_processes_are_finished(pipeline_run):
    for proc in pipeline_run.processes:
        assert not proc.is_alive(), f"Process '{proc.name}' is still alive"
