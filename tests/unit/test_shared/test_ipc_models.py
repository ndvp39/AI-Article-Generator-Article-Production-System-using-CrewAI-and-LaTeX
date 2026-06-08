from __future__ import annotations

import time
import uuid

import pytest

from article_generator.shared.ipc_models import AgentMessage, AgentStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message(**kwargs) -> AgentMessage:
    defaults = {"sender": "researcher", "recipient": "writer", "content": "outline", "topic": "AI"}
    return AgentMessage(**{**defaults, **kwargs})


def _make_status(**kwargs) -> AgentStatus:
    defaults = {"agent_name": "researcher", "pid": 12345, "status": "running", "started_at": time.time()}
    return AgentStatus(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# AgentMessage — field assignment
# ---------------------------------------------------------------------------

def test_agent_message_explicit_fields_stored():
    msg = AgentMessage(
        sender="researcher",
        recipient="writer",
        content="outline text",
        topic="AI in Healthcare",
        message_type="output",
    )
    assert msg.sender == "researcher"
    assert msg.recipient == "writer"
    assert msg.content == "outline text"
    assert msg.topic == "AI in Healthcare"
    assert msg.message_type == "output"


def test_agent_message_default_message_type_is_output():
    msg = _make_message()
    assert msg.message_type == "output"


def test_agent_message_message_type_input():
    msg = _make_message(message_type="input")
    assert msg.message_type == "input"


def test_agent_message_message_type_error():
    msg = _make_message(message_type="error")
    assert msg.message_type == "error"


# ---------------------------------------------------------------------------
# AgentMessage — message_id (UUID)
# ---------------------------------------------------------------------------

def test_agent_message_id_is_valid_uuid():
    msg = _make_message()
    parsed = uuid.UUID(msg.message_id)  # raises ValueError if not valid UUID
    assert str(parsed) == msg.message_id


def test_agent_message_ids_are_unique_per_instance():
    ids = {_make_message().message_id for _ in range(20)}
    assert len(ids) == 20, "Each AgentMessage must receive a distinct UUID"


def test_agent_message_id_can_be_overridden():
    fixed = "00000000-0000-0000-0000-000000000001"
    msg = AgentMessage(sender="a", recipient="b", content="c", topic="t", message_id=fixed)
    assert msg.message_id == fixed


# ---------------------------------------------------------------------------
# AgentMessage — timestamp
# ---------------------------------------------------------------------------

def test_agent_message_timestamp_is_recent():
    before = time.time()
    msg = _make_message()
    after = time.time()
    assert before <= msg.timestamp <= after


def test_agent_message_timestamps_increase_over_time():
    msg_a = _make_message()
    time.sleep(0.01)
    msg_b = _make_message()
    assert msg_b.timestamp >= msg_a.timestamp


# ---------------------------------------------------------------------------
# AgentStatus — field assignment
# ---------------------------------------------------------------------------

def test_agent_status_fields_stored():
    t = time.time()
    status = AgentStatus(agent_name="writer", pid=42, status="running", started_at=t)
    assert status.agent_name == "writer"
    assert status.pid == 42
    assert status.status == "running"
    assert status.started_at == t
    assert status.finished_at is None


def test_agent_status_pid_can_be_none():
    status = _make_status(pid=None)
    assert status.pid is None


def test_agent_status_finished_at_can_be_set():
    t_start = time.time()
    t_end = t_start + 5.0
    status = AgentStatus(agent_name="editor", pid=99, status="done", started_at=t_start, finished_at=t_end)
    assert status.finished_at == t_end


@pytest.mark.parametrize("s", ["running", "done", "error", "timeout"])
def test_agent_status_valid_status_values(s: str):
    status = _make_status(status=s)
    assert status.status == s
