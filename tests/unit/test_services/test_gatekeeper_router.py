from __future__ import annotations

import queue
import time
from multiprocessing import Queue

import pytest

from article_generator.services.gatekeeper_router import (
    GatekeeperRouter,
    GatekeeperValidationError,
)
from article_generator.shared.ipc_models import AgentMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_NAMES = [
    "researcher",
    "writer",
    "editor",
    "graph_generator",
    "latex_formatter",
    "bidi_specialist",
]


def _make_pipeline(n: int) -> list[tuple[Queue, Queue]]:
    return [(Queue(), Queue()) for _ in range(n)]


def _msg(
    sender: str,
    content: str = "some content",
    topic: str = "AI",
    message_type: str = "output",
) -> AgentMessage:
    return AgentMessage(sender=sender, recipient="", content=content, topic=topic, message_type=message_type)


def _make_router(n: int = 2) -> tuple[GatekeeperRouter, list[tuple[Queue, Queue]]]:
    qs = _make_pipeline(n)
    router = GatekeeperRouter(pipeline=qs, agent_names=_AGENT_NAMES[:n])
    return router, qs


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

def test_constructor_raises_on_length_mismatch():
    qs = _make_pipeline(3)
    with pytest.raises(ValueError, match="same length"):
        GatekeeperRouter(pipeline=qs, agent_names=["a", "b"])


def test_last_error_initially_none():
    router, _ = _make_router()
    assert router.last_error is None


# ---------------------------------------------------------------------------
# _validate — happy paths
# ---------------------------------------------------------------------------

def test_validate_accepts_valid_output_message():
    router, _ = _make_router(2)
    router._validate(_msg("researcher"), expected_sender="researcher")  # must not raise


def test_validate_accepts_input_message_type():
    router, _ = _make_router(2)
    router._validate(_msg("researcher", message_type="input"), expected_sender="researcher")


@pytest.mark.parametrize("mtype", ["input", "output", "error"])
def test_validate_accepts_all_valid_message_types(mtype: str):
    router, _ = _make_router(2)
    content = "" if mtype == "error" else "non-empty"
    router._validate(_msg("researcher", content=content, message_type=mtype), expected_sender="researcher")


def test_validate_allows_empty_content_for_error_messages():
    router, _ = _make_router(2)
    router._validate(
        _msg("researcher", content="", message_type="error"),
        expected_sender="researcher",
    )  # must not raise


# ---------------------------------------------------------------------------
# _validate — error paths
# ---------------------------------------------------------------------------

def test_validate_raises_on_empty_content():
    router, _ = _make_router(2)
    with pytest.raises(GatekeeperValidationError, match="empty content"):
        router._validate(_msg("researcher", content=""), expected_sender="researcher")


def test_validate_raises_on_whitespace_only_content():
    router, _ = _make_router(2)
    with pytest.raises(GatekeeperValidationError, match="empty content"):
        router._validate(_msg("researcher", content="   "), expected_sender="researcher")


def test_validate_raises_on_wrong_sender():
    router, _ = _make_router(2)
    with pytest.raises(GatekeeperValidationError, match="Expected sender"):
        router._validate(_msg("unknown_agent"), expected_sender="researcher")


def test_validate_raises_on_invalid_message_type():
    router, _ = _make_router(2)
    with pytest.raises(GatekeeperValidationError, match="Invalid message_type"):
        router._validate(
            AgentMessage(sender="researcher", recipient="", content="x", topic="AI", message_type="INVALID"),
            expected_sender="researcher",
        )


# ---------------------------------------------------------------------------
# _route — field checks
# ---------------------------------------------------------------------------

def test_route_puts_message_on_dest_queue():
    router, qs = _make_router(2)
    msg = _msg("researcher")
    dest = qs[1][0]
    router._route(msg, dest, step=0)
    result = dest.get(timeout=2.0)
    assert result.content == "some content"


def test_route_sets_recipient_to_next_agent():
    router, qs = _make_router(2)
    dest = qs[1][0]
    router._route(_msg("researcher"), dest, step=0)
    result = dest.get(timeout=2.0)
    assert result.recipient == "writer"


def test_route_preserves_sender_content_topic():
    router, qs = _make_router(3)
    dest = qs[1][0]
    router._route(_msg("researcher", content="outline", topic="Climate"), dest, step=0)
    result = dest.get(timeout=2.0)
    assert result.sender == "researcher"
    assert result.content == "outline"
    assert result.topic == "Climate"


def test_route_preserves_message_id():
    router, qs = _make_router(2)
    msg = _msg("researcher")
    original_id = msg.message_id
    dest = qs[1][0]
    router._route(msg, dest, step=0)
    result = dest.get(timeout=2.0)
    assert result.message_id == original_id


# ---------------------------------------------------------------------------
# Routing thread — single hop
# ---------------------------------------------------------------------------

def test_thread_routes_single_message():
    router, qs = _make_router(2)
    router.start()
    try:
        qs[0][1].put(_msg("researcher", content="research done"))
        result = qs[1][0].get(timeout=3.0)
        assert result.recipient == "writer"
        assert result.content == "research done"
    finally:
        router.stop()


def test_thread_routing_sets_no_error_on_valid_message():
    router, qs = _make_router(2)
    router.start()
    try:
        qs[0][1].put(_msg("researcher"))
        qs[1][0].get(timeout=3.0)
        assert router.last_error is None
    finally:
        router.stop()


# ---------------------------------------------------------------------------
# Routing thread — all 5 hops (full 6-agent pipeline)
# ---------------------------------------------------------------------------

def test_all_five_hops_route_in_order():
    qs = _make_pipeline(6)
    router = GatekeeperRouter(pipeline=qs, agent_names=_AGENT_NAMES)
    router.start()
    try:
        outputs = [
            ("researcher",      "research outline"),
            ("writer",          "full article draft"),
            ("editor",          "reviewed article"),
            ("graph_generator", "graph code"),
            ("latex_formatter", "tex content"),
        ]
        for sender, content in outputs:
            # Find which step this sender belongs to
            step = _AGENT_NAMES.index(sender)
            qs[step][1].put(_msg(sender, content=content))
            # Small delay to let the router thread process before we feed the next
            time.sleep(0.05)

        # Collect routed messages from each destination queue (in_queues 1-5)
        expected_recipients = _AGENT_NAMES[1:]
        for i, expected_recipient in enumerate(expected_recipients):
            result = qs[i + 1][0].get(timeout=3.0)
            assert result.recipient == expected_recipient, (
                f"Hop {i}: expected recipient '{expected_recipient}', got '{result.recipient}'"
            )

        assert router.last_error is None
    finally:
        router.stop()


def test_routing_order_matches_sequential_pipeline():
    qs = _make_pipeline(6)
    router = GatekeeperRouter(pipeline=qs, agent_names=_AGENT_NAMES)
    router.start()
    try:
        # Feed all outputs in pipeline order
        for i, name in enumerate(_AGENT_NAMES[:-1]):
            qs[i][1].put(_msg(name, content=f"output from {name}"))
            time.sleep(0.05)

        # Verify each subsequent agent received the correct content
        for i, name in enumerate(_AGENT_NAMES[:-1]):
            result = qs[i + 1][0].get(timeout=3.0)
            assert result.content == f"output from {name}"
    finally:
        router.stop()


# ---------------------------------------------------------------------------
# Routing thread — validation error stops routing
# ---------------------------------------------------------------------------

def test_validation_error_sets_last_error():
    router, qs = _make_router(3)
    router.start()
    try:
        # Put a message with the wrong sender — step 0 expects "researcher"
        qs[0][1].put(_msg("wrong_agent", content="some content"))
        time.sleep(0.2)  # give thread time to process
        assert router.last_error is not None
        assert isinstance(router.last_error, GatekeeperValidationError)
    finally:
        router.stop()


def test_validation_error_message_not_forwarded():
    router, qs = _make_router(3)
    router.start()
    try:
        qs[0][1].put(_msg("wrong_agent", content="some content"))
        time.sleep(0.2)
        # The bad message must NOT appear in the next queue
        with pytest.raises(queue.Empty):
            qs[1][0].get(timeout=0.3)
    finally:
        router.stop()


def test_empty_content_error_stops_routing():
    router, qs = _make_router(3)
    router.start()
    try:
        qs[0][1].put(_msg("researcher", content=""))
        time.sleep(0.2)
        assert router.last_error is not None
    finally:
        router.stop()


def test_stop_event_exits_loop_cleanly():
    """Covers the stop_event.is_set() break (line 78): stop before any message arrives."""
    router, _ = _make_router(2)
    router.start()
    router.stop()  # signal stop with no messages — thread must exit without error
    assert router.last_error is None


def test_queue_timeout_retry_then_routes():
    """Covers queue.Empty / continue (lines 84-85): message arrives after the first 1-s timeout."""
    router, qs = _make_router(2)
    router.start()
    try:
        time.sleep(1.2)  # let the first get(timeout=1.0) expire
        qs[0][1].put(_msg("researcher", content="late message"))
        result = qs[1][0].get(timeout=3.0)
        assert result.content == "late message"
    finally:
        router.stop()
