from __future__ import annotations

import dataclasses
import logging
import threading
import time

from article_generator.constants import WATCHDOG_POLL_INTERVAL_SECONDS
from article_generator.shared.ipc_models import AgentStatus
from article_generator.shared.process_runner import AgentProcessRunner

logger = logging.getLogger(__name__)


class AgentTimeoutError(Exception):
    """Raised (stored) when an agent process exceeds its wall-clock timeout."""


class Watchdog:
    """Daemon thread that monitors agent processes and enforces per-agent timeouts.

    Poll cycle (every `poll_interval` seconds):
    - If process is alive and elapsed > runner.timeout  → terminate + status="timeout"
    - If process is dead with exitcode == 0             → status="done"
    - If process is dead with exitcode != 0             → status="error"
    """

    def __init__(
        self,
        runners: list[AgentProcessRunner],
        poll_interval: float = WATCHDOG_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._runners = runners
        self._poll_interval = poll_interval
        self._statuses: dict[str, AgentStatus] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: AgentTimeoutError | None = None

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Initialise status records and start the daemon thread."""
        now = time.time()
        for runner in self._runners:
            self._statuses[runner.agent_name] = AgentStatus(
                agent_name=runner.agent_name,
                pid=runner.pid,       # None if process not yet spawned
                status="running",
                started_at=now,
            )
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="watchdog",
        )
        self._thread.start()
        logger.info("Watchdog started monitoring %d agents", len(self._runners))

    def stop(self) -> None:
        """Signal the daemon thread to exit and wait up to 5 s."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        logger.info("Watchdog stopped")

    # ------------------------------------------------------------------
    # Public status API
    # ------------------------------------------------------------------

    def get_status(self, agent_name: str) -> AgentStatus:
        """Return the current AgentStatus for the named agent."""
        return self._statuses[agent_name]

    def all_healthy(self) -> bool:
        """Return True if no agent has status 'error' or 'timeout'."""
        return all(s.status not in ("error", "timeout") for s in self._statuses.values())

    @property
    def last_error(self) -> AgentTimeoutError | None:
        """Most recent AgentTimeoutError recorded, or None."""
        return self._last_error

    # ------------------------------------------------------------------
    # Daemon thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Poll every poll_interval seconds; exit when stop_event is set."""
        while not self._stop_event.wait(self._poll_interval):
            for runner in self._runners:
                self._check_runner(runner)

    def _check_runner(self, runner: AgentProcessRunner) -> None:
        name = runner.agent_name
        status = self._statuses.get(name)

        if status is None or status.status != "running":
            return  # not registered yet or already resolved

        # Process not yet spawned — skip until pid is available
        if runner.pid is None:
            return

        # Backfill pid once process starts (if Watchdog started before spawn)
        if status.pid is None:
            self._statuses[name] = dataclasses.replace(status, pid=runner.pid)
            status = self._statuses[name]

        if runner.is_alive():
            elapsed = time.time() - status.started_at
            if elapsed > runner.timeout:
                runner.terminate()
                self._statuses[name] = dataclasses.replace(
                    status, status="timeout", finished_at=time.time()
                )
                err = AgentTimeoutError(
                    f"Agent '{name}' timed out after {elapsed:.1f}s "
                    f"(limit={runner.timeout}s)"
                )
                self._last_error = err
                logger.error("Watchdog: %s", err)
        else:
            # Process has exited — distinguish normal vs crash
            code = runner.exitcode
            new_status = "done" if code == 0 else "error"
            self._statuses[name] = dataclasses.replace(
                status, status=new_status, finished_at=time.time()
            )
            if new_status == "error":
                logger.error(
                    "Watchdog: agent '%s' died unexpectedly (exit code %s)", name, code
                )
            else:
                logger.debug("Watchdog: agent '%s' completed normally", name)
