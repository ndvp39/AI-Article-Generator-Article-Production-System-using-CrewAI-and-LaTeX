from __future__ import annotations

import dataclasses
import logging
import queue
import threading
from multiprocessing import Queue

from article_generator.shared.ipc_models import AgentMessage

logger = logging.getLogger(__name__)

_VALID_MESSAGE_TYPES = frozenset({"input", "output", "error"})


class GatekeeperValidationError(Exception):
    """Raised when an AgentMessage fails schema or ordering checks."""


class GatekeeperRouter:
    """Daemon thread that validates and routes AgentMessage objects between queues.

    Iterates through the pipeline in order: reads each agent's Q_out, validates
    the message, fills in the recipient, and puts it into the next agent's Q_in.
    Covers steps 0 → N-2 (the final agent's output is collected by the orchestrator).
    """

    def __init__(
        self,
        pipeline: list[tuple[Queue, Queue]],
        agent_names: list[str],
    ) -> None:
        if len(pipeline) != len(agent_names):
            raise ValueError("pipeline and agent_names must have the same length")
        self._pipeline = pipeline
        self._agent_names = agent_names
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: GatekeeperValidationError | None = None

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the daemon thread."""
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="gatekeeper-router",
        )
        self._thread.start()
        logger.info("GatekeeperRouter started")

    def stop(self) -> None:
        """Signal the daemon thread to exit and wait up to 5 s for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        logger.info("GatekeeperRouter stopped")

    @property
    def last_error(self) -> GatekeeperValidationError | None:
        """Last validation error encountered by the router thread, or None."""
        return self._last_error

    # ------------------------------------------------------------------
    # Internal routing loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Read each Q_out in pipeline order, validate, route to next Q_in."""
        step = 0
        n_steps = len(self._pipeline) - 1  # last agent's output not routed here

        while step < n_steps:
            if self._stop_event.is_set():
                break

            q_out = self._pipeline[step][1]

            try:
                msg: AgentMessage = q_out.get(timeout=1.0)
            except queue.Empty:
                continue  # retry same step — Watchdog handles wall-clock timeouts

            expected_sender = self._agent_names[step]
            try:
                self._validate(msg, expected_sender)
            except GatekeeperValidationError as exc:
                logger.error(
                    "GatekeeperRouter validation error at step %d (%s): %s",
                    step, expected_sender, exc,
                )
                self._last_error = exc
                break

            q_in_next = self._pipeline[step + 1][0]
            self._route(msg, q_in_next, step)
            step += 1

    # ------------------------------------------------------------------
    # Validation and routing
    # ------------------------------------------------------------------

    def _validate(self, msg: AgentMessage, expected_sender: str) -> None:
        """Raise GatekeeperValidationError if msg fails any schema check."""
        if msg.message_type not in _VALID_MESSAGE_TYPES:
            raise GatekeeperValidationError(
                f"Invalid message_type '{msg.message_type}'; "
                f"must be one of {sorted(_VALID_MESSAGE_TYPES)}"
            )
        if msg.message_type != "error" and not msg.content.strip():
            raise GatekeeperValidationError(
                f"AgentMessage from '{msg.sender}' has empty content"
            )
        if msg.sender != expected_sender:
            raise GatekeeperValidationError(
                f"Expected sender '{expected_sender}', got '{msg.sender}'"
            )

    def _route(self, msg: AgentMessage, dest_queue: Queue, step: int) -> None:
        """Fill in recipient, put message on dest_queue, and log the hop."""
        next_name = self._agent_names[step + 1]
        routed = dataclasses.replace(msg, recipient=next_name)
        dest_queue.put(routed)
        logger.info(
            "Routed step %d: %s → %s (%d chars)",
            step, msg.sender, next_name, len(msg.content),
        )
