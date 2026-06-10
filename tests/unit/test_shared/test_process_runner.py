from __future__ import annotations

import sys
from multiprocessing import Queue
from unittest.mock import MagicMock, patch

import pytest

from article_generator.shared.ipc_models import AgentMessage
from article_generator.shared.process_runner import AgentProcessRunner, _agent_subprocess

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeAgentCls:
    """Minimal agent builder that never touches crewai at construction time."""
    def __init__(self, llm=None) -> None:
        self._llm = llm

    def build(self) -> MagicMock:
        return MagicMock(name="fake_crewai_agent")


def _make_runner(**kwargs) -> AgentProcessRunner:
    defaults = {
        "agent_cls": _FakeAgentCls,
        "task_description": "Research {topic}",
        "expected_output": "Outline",
        "in_queue": Queue(),
        "out_queue": Queue(),
        "agent_name": "researcher",
        "timeout": 60,
    }
    defaults.update(kwargs)
    return AgentProcessRunner(**defaults)


def _mock_crewai_and_llm(raw_output: str = "article content") -> dict:
    """Return sys.modules patches replacing crewai and llm_factory with mocks."""
    mock_crewai = MagicMock(name="crewai")
    mock_crewai.Process = MagicMock(name="crewai.Process")
    mock_crew_instance = MagicMock(name="crew_instance")
    mock_crew_instance.kickoff.return_value.raw = raw_output
    mock_crewai.Crew.return_value = mock_crew_instance

    mock_llm_factory = MagicMock(name="llm_factory")
    mock_llm_factory.build_llm.return_value = MagicMock(name="llm")

    return {
        "crewai": mock_crewai,
        "article_generator.shared.llm_factory": mock_llm_factory,
    }


# ---------------------------------------------------------------------------
# pid — before and after start
# ---------------------------------------------------------------------------

def test_pid_is_none_before_start():
    runner = _make_runner()
    assert runner.pid is None


def test_pid_returns_process_pid_after_start():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        MockProc.return_value.pid = 7777
        runner = _make_runner()
        runner.start()
        assert runner.pid == 7777


# ---------------------------------------------------------------------------
# is_alive
# ---------------------------------------------------------------------------

def test_is_alive_false_before_start():
    assert _make_runner().is_alive() is False


def test_is_alive_true_when_process_running():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        MockProc.return_value.is_alive.return_value = True
        runner = _make_runner()
        runner.start()
        assert runner.is_alive() is True


def test_is_alive_false_when_process_finished():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        MockProc.return_value.is_alive.return_value = False
        runner = _make_runner()
        runner.start()
        assert runner.is_alive() is False


# ---------------------------------------------------------------------------
# start — process creation
# ---------------------------------------------------------------------------

def test_start_spawns_process_with_subprocess_function():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        runner = _make_runner()
        runner.start()
        MockProc.assert_called_once()
        call_kwargs = MockProc.call_args.kwargs
        assert call_kwargs["target"] is _agent_subprocess


def test_start_spawns_process_with_agent_class_in_args():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        runner = _make_runner()
        runner.start()
        args = MockProc.call_args.kwargs["args"]
        assert args[0] is _FakeAgentCls


def test_start_calls_process_start():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        runner = _make_runner()
        runner.start()
        MockProc.return_value.start.assert_called_once()


# ---------------------------------------------------------------------------
# terminate
# ---------------------------------------------------------------------------

def test_terminate_kills_alive_process():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        MockProc.return_value.is_alive.return_value = True
        runner = _make_runner()
        runner.start()
        runner.terminate()
        MockProc.return_value.terminate.assert_called_once()


def test_terminate_skips_dead_process():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        MockProc.return_value.is_alive.return_value = False
        runner = _make_runner()
        runner.start()
        runner.terminate()
        MockProc.return_value.terminate.assert_not_called()


def test_terminate_before_start_does_not_raise():
    runner = _make_runner()
    runner.terminate()  # must not raise


# ---------------------------------------------------------------------------
# join
# ---------------------------------------------------------------------------

def test_join_delegates_to_process():
    with patch("article_generator.shared.process_runner.Process") as MockProc:
        runner = _make_runner()
        runner.start()
        runner.join(timeout=3.0)
        MockProc.return_value.join.assert_called_once_with(timeout=3.0)


def test_join_before_start_does_not_raise():
    _make_runner().join()  # must not raise


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def test_agent_name_uses_explicit_name():
    assert _make_runner(agent_name="editor").agent_name == "editor"


def test_agent_name_defaults_to_class_name():
    runner = AgentProcessRunner(
        agent_cls=_FakeAgentCls,
        task_description="Do {topic}",
        expected_output="Done",
        in_queue=Queue(),
        out_queue=Queue(),
    )
    assert runner.agent_name == "_FakeAgentCls"


def test_timeout_property():
    assert _make_runner(timeout=180).timeout == 180


# ---------------------------------------------------------------------------
# _agent_subprocess — happy path (in-process, crewai mocked via sys.modules)
# ---------------------------------------------------------------------------

def test_subprocess_writes_output_message_to_out_queue():
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(sender="orchestrator", recipient="researcher", content="", topic="AI"))

    with patch.dict(sys.modules, _mock_crewai_and_llm("research outline")):
        _agent_subprocess(
            agent_cls=_FakeAgentCls,
            task_description="Research {topic}",
            expected_output="Outline",
            in_queue=q_in,
            out_queue=q_out,
            agent_name="researcher",
            llm_kwargs={},
        )

    # Use get(timeout) rather than empty()+get_nowait(): multiprocessing.Queue
    # uses an internal feeder thread so empty() may return True for a brief
    # window after put() before the item reaches the underlying pipe.
    out_msg: AgentMessage = q_out.get(timeout=2.0)
    assert isinstance(out_msg, AgentMessage)
    assert out_msg.sender == "researcher"
    assert out_msg.content == "research outline"
    assert out_msg.topic == "AI"
    assert out_msg.message_type == "output"


def test_subprocess_topic_propagated_from_input_message():
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(sender="orch", recipient="researcher", content="", topic="Climate Change"))

    with patch.dict(sys.modules, _mock_crewai_and_llm()):
        _agent_subprocess(
            agent_cls=_FakeAgentCls,
            task_description="Research {topic}",
            expected_output="Outline",
            in_queue=q_in,
            out_queue=q_out,
            agent_name="researcher",
            llm_kwargs={},
        )

    assert q_out.get(timeout=2.0).topic == "Climate Change"


# ---------------------------------------------------------------------------
# _agent_subprocess — error path
# ---------------------------------------------------------------------------

def test_subprocess_error_puts_error_message_on_queue():
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(sender="orch", recipient="researcher", content="", topic="AI"))

    bad_mocks = _mock_crewai_and_llm()
    bad_mocks["crewai"].Crew.side_effect = RuntimeError("LLM unavailable")

    with patch.dict(sys.modules, bad_mocks):
        with pytest.raises(RuntimeError, match="LLM unavailable"):
            _agent_subprocess(
                agent_cls=_FakeAgentCls,
                task_description="Research {topic}",
                expected_output="Outline",
                in_queue=q_in,
                out_queue=q_out,
                agent_name="researcher",
                llm_kwargs={},
            )

    err_msg: AgentMessage = q_out.get(timeout=2.0)
    assert err_msg.message_type == "error"
    assert err_msg.sender == "researcher"
    assert err_msg.recipient == "orchestrator"
    assert "RuntimeError" in err_msg.content


def test_subprocess_error_message_contains_traceback():
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(sender="orch", recipient="researcher", content="", topic="AI"))

    bad_mocks = _mock_crewai_and_llm()
    bad_mocks["crewai"].Crew.side_effect = ValueError("bad config")

    with patch.dict(sys.modules, bad_mocks):
        with pytest.raises(ValueError):
            _agent_subprocess(
                agent_cls=_FakeAgentCls,
                task_description="Do {topic}",
                expected_output="Result",
                in_queue=q_in,
                out_queue=q_out,
                agent_name="writer",
                llm_kwargs={},
            )

    err_msg: AgentMessage = q_out.get(timeout=2.0)
    assert "Traceback" in err_msg.content
    assert "bad config" in err_msg.content


# ---------------------------------------------------------------------------
# _agent_subprocess — upstream error short-circuit
# ---------------------------------------------------------------------------

def test_subprocess_propagates_upstream_error_without_llm_work():
    """When the input message is already an error, no LLM is built and the
    error is forwarded immediately to the output queue."""
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(
        sender="researcher", recipient="writer",
        content="upstream crash traceback", topic="AI",
        message_type="error",
    ))

    mocks = _mock_crewai_and_llm()
    with patch.dict(sys.modules, mocks):
        _agent_subprocess(
            agent_cls=_FakeAgentCls,
            task_description="Write {topic}",
            expected_output="Article",
            in_queue=q_in,
            out_queue=q_out,
            agent_name="writer",
            llm_kwargs={},
        )

    out_msg: AgentMessage = q_out.get(timeout=2.0)
    assert out_msg.message_type == "error"
    assert out_msg.content == "upstream crash traceback"
    assert out_msg.topic == "AI"
    # No LLM or Crew was created
    assert mocks["article_generator.shared.llm_factory"].build_llm.call_count == 0
    assert mocks["crewai"].Crew.call_count == 0


def test_subprocess_upstream_error_preserves_content_and_topic():
    q_in, q_out = Queue(), Queue()
    q_in.put(AgentMessage(
        sender="writer", recipient="editor",
        content="something went wrong", topic="Climate",
        message_type="error",
    ))

    with patch.dict(sys.modules, _mock_crewai_and_llm()):
        _agent_subprocess(
            agent_cls=_FakeAgentCls,
            task_description="Edit {topic}",
            expected_output="Edited",
            in_queue=q_in,
            out_queue=q_out,
            agent_name="editor",
            llm_kwargs={},
        )

    out_msg: AgentMessage = q_out.get(timeout=2.0)
    assert out_msg.content == "something went wrong"
    assert out_msg.topic == "Climate"
    assert out_msg.sender == "editor"
