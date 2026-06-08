from __future__ import annotations

import queue as queue_module
import threading
import time
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.process_orchestrator import (
    _N_AGENTS,
    _PIPELINE_SPEC,
    ProcessOrchestrator,
)
from article_generator.shared.ipc_models import AgentMessage
from article_generator.shared.models import ArticleResult

_BASE = "article_generator.services.process_orchestrator"
_CFG = {"agents": {"temperature": "0.7"}}


# ---------------------------------------------------------------------------
# Context manager: patches all heavy deps + injects the final message
# ---------------------------------------------------------------------------

@contextmanager
def _mocked_run(
    topic: str = "AI",
    final_content: str = "final tex content",
    message_type: str = "output",
    watchdog_healthy: bool = True,
    router_error=None,
    watchdog_error=None,
):
    """Patch AgentProcessRunner / GatekeeperRouter / Watchdog and inject the
    final AgentMessage into the bidi specialist's output queue once the
    pipeline has been created.
    """
    orch = ProcessOrchestrator(config=_CFG)

    final_msg = AgentMessage(
        sender="bidi_specialist",
        recipient="orchestrator",
        content=final_content,
        topic=topic,
        message_type=message_type,
    )

    with ExitStack() as stack:
        MockRunner = stack.enter_context(patch(_BASE + ".AgentProcessRunner"))
        MockRunner.return_value.is_alive.return_value = False
        MockRouter = stack.enter_context(patch(_BASE + ".GatekeeperRouter"))
        MockWatchdog = stack.enter_context(patch(_BASE + ".Watchdog"))
        MockWatchdog.return_value.all_healthy.return_value = watchdog_healthy
        MockWatchdog.return_value.last_error = watchdog_error
        MockRouter.return_value.last_error = router_error

        def _inject():
            # Wait until _run_pipeline has created the queue pairs, then put
            # the final message into the last agent's output queue.
            while not orch._pipeline:
                time.sleep(0.005)
            orch._pipeline[_N_AGENTS - 1][1].put(final_msg)

        t = threading.Thread(target=_inject, daemon=True)
        t.start()
        try:
            yield orch, MockRunner, MockRouter, MockWatchdog
        finally:
            t.join(timeout=2)


# ---------------------------------------------------------------------------
# __init__ — config extraction
# ---------------------------------------------------------------------------

def test_llm_kwargs_temperature_derived_from_config():
    orch = ProcessOrchestrator(config={"agents": {"temperature": "0.3"}})
    assert orch._llm_kwargs == {"temperature": 0.3}


def test_llm_kwargs_explicit_override_takes_precedence():
    orch = ProcessOrchestrator(config=_CFG, llm_kwargs={"temperature": 0.9, "key": "x"})
    assert orch._llm_kwargs == {"temperature": 0.9, "key": "x"}


def test_llm_kwargs_default_temperature_when_agents_key_missing():
    orch = ProcessOrchestrator(config={})
    assert orch._llm_kwargs["temperature"] == 0.7


# ---------------------------------------------------------------------------
# _PIPELINE_SPEC — module-level constant shape
# ---------------------------------------------------------------------------

def test_pipeline_spec_has_six_entries():
    assert _N_AGENTS == 6


def test_pipeline_spec_agent_names_in_order():
    names = [spec[3] for spec in _PIPELINE_SPEC]
    assert names == [
        "researcher", "writer", "editor",
        "graph_generator", "latex_formatter", "bidi_specialist",
    ]


# ---------------------------------------------------------------------------
# _shutdown — direct method tests
# ---------------------------------------------------------------------------

def test_shutdown_stops_router():
    orch = ProcessOrchestrator(config=_CFG)
    orch._router = MagicMock()
    orch._watchdog = None
    orch._runners = []
    orch._shutdown()
    orch._router.stop.assert_called_once()


def test_shutdown_stops_watchdog():
    orch = ProcessOrchestrator(config=_CFG)
    orch._router = None
    orch._watchdog = MagicMock()
    orch._runners = []
    orch._shutdown()
    orch._watchdog.stop.assert_called_once()


def test_shutdown_joins_every_runner():
    orch = ProcessOrchestrator(config=_CFG)
    orch._router = None
    orch._watchdog = None
    runners = [MagicMock(is_alive=MagicMock(return_value=False)) for _ in range(3)]
    orch._runners = runners
    orch._shutdown()
    for r in runners:
        r.join.assert_called_once_with(timeout=5.0)


def test_shutdown_terminates_alive_runner():
    orch = ProcessOrchestrator(config=_CFG)
    orch._router = None
    orch._watchdog = None
    runner = MagicMock()
    runner.is_alive.return_value = True
    orch._runners = [runner]
    orch._shutdown()
    runner.terminate.assert_called_once()


def test_shutdown_skips_terminate_for_dead_runner():
    orch = ProcessOrchestrator(config=_CFG)
    orch._router = None
    orch._watchdog = None
    runner = MagicMock()
    runner.is_alive.return_value = False
    orch._runners = [runner]
    orch._shutdown()
    runner.terminate.assert_not_called()


def test_shutdown_safe_with_no_router_or_watchdog():
    orch = ProcessOrchestrator(config=_CFG)
    orch._shutdown()  # must not raise when router/watchdog are None


# ---------------------------------------------------------------------------
# _raise_pipeline_error
# ---------------------------------------------------------------------------

def test_raise_pipeline_error_raises_runtime_error():
    orch = ProcessOrchestrator(config=_CFG)
    with pytest.raises(RuntimeError, match="reason text"):
        orch._raise_pipeline_error("reason text")


def test_raise_pipeline_error_calls_shutdown_first():
    orch = ProcessOrchestrator(config=_CFG)
    orch._shutdown = MagicMock()
    with pytest.raises(RuntimeError):
        orch._raise_pipeline_error("boom")
    orch._shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# run() — six processes spawned and started
# ---------------------------------------------------------------------------

def test_run_creates_six_runner_instances():
    with _mocked_run() as (orch, MockRunner, _, __):
        orch.run("AI")
    assert MockRunner.call_count == 6


def test_run_starts_all_six_runners():
    with _mocked_run() as (orch, MockRunner, _, __):
        orch.run("AI")
    assert MockRunner.return_value.start.call_count == 6


def test_run_starts_gatekeeper_router():
    with _mocked_run() as (orch, _, MockRouter, __):
        orch.run("AI")
    MockRouter.return_value.start.assert_called_once()


def test_run_starts_watchdog():
    with _mocked_run() as (orch, _, __, MockWatchdog):
        orch.run("AI")
    MockWatchdog.return_value.start.assert_called_once()


# ---------------------------------------------------------------------------
# run() — initial message injection
# ---------------------------------------------------------------------------

def test_run_injects_initial_message_into_researcher_queue():
    with _mocked_run(topic="Quantum") as (orch, *_):
        orch.run("Quantum")
    initial = orch._pipeline[0][0].get(timeout=1.0)
    assert initial.sender == "orchestrator"
    assert initial.recipient == "researcher"


def test_run_initial_message_content_is_topic():
    with _mocked_run(topic="Quantum") as (orch, *_):
        orch.run("Quantum")
    initial = orch._pipeline[0][0].get(timeout=1.0)
    assert initial.content == "Quantum"


def test_run_initial_message_topic_field_matches_topic():
    with _mocked_run(topic="Quantum") as (orch, *_):
        orch.run("Quantum")
    initial = orch._pipeline[0][0].get(timeout=1.0)
    assert initial.topic == "Quantum"


def test_run_initial_message_type_is_input():
    with _mocked_run() as (orch, *_):
        orch.run("AI")
    initial = orch._pipeline[0][0].get(timeout=1.0)
    assert initial.message_type == "input"


# ---------------------------------------------------------------------------
# run() — success path return value
# ---------------------------------------------------------------------------

def test_run_returns_article_result():
    with _mocked_run() as (orch, *_):
        result = orch.run("AI")
    assert isinstance(result, ArticleResult)
    assert result.success is True


def test_run_markdown_content_comes_from_final_message():
    with _mocked_run(final_content="the full generated article") as (orch, *_):
        result = orch.run("AI")
    assert result.markdown_content == "the full generated article"


def test_run_shutdown_called_on_success():
    with _mocked_run() as (orch, _, MockRouter, MockWatchdog):
        orch.run("AI")
    MockRouter.return_value.stop.assert_called()
    MockWatchdog.return_value.stop.assert_called()


# ---------------------------------------------------------------------------
# run() — error paths
# ---------------------------------------------------------------------------

def test_run_raises_when_final_message_type_is_error():
    with _mocked_run(message_type="error", final_content="agent crashed") as (orch, *_):
        with pytest.raises(RuntimeError, match="Pipeline failed"):
            orch.run("AI")


def test_run_raises_when_watchdog_unhealthy():
    with _mocked_run(watchdog_healthy=False) as (orch, *_):
        with pytest.raises(RuntimeError, match="crashed or timed out"):
            orch.run("AI")


def test_run_raises_on_router_validation_error():
    err = Exception("bad schema")
    with _mocked_run(router_error=err) as (orch, *_):
        with pytest.raises(RuntimeError, match="GatekeeperRouter"):
            orch.run("AI")


def test_run_calls_shutdown_when_runner_raises():
    orch = ProcessOrchestrator(config=_CFG)
    orch._shutdown = MagicMock()

    with ExitStack() as stack:
        stack.enter_context(
            patch(_BASE + ".AgentProcessRunner", side_effect=RuntimeError("spawn failed"))
        )
        stack.enter_context(patch(_BASE + ".GatekeeperRouter"))
        stack.enter_context(patch(_BASE + ".Watchdog"))

        with pytest.raises(RuntimeError, match="spawn failed"):
            orch.run("AI")

    orch._shutdown.assert_called()


def test_run_raises_pipeline_error_on_queue_timeout():
    orch = ProcessOrchestrator(config=_CFG)

    mock_q = MagicMock()
    mock_q.get.side_effect = queue_module.Empty()

    with ExitStack() as stack:
        stack.enter_context(patch(_BASE + ".AgentProcessRunner"))
        stack.enter_context(patch(_BASE + ".GatekeeperRouter"))
        stack.enter_context(patch(_BASE + ".Watchdog"))
        stack.enter_context(patch(_BASE + ".Queue", return_value=mock_q))

        with pytest.raises(RuntimeError, match="Pipeline error"):
            orch.run("AI")
