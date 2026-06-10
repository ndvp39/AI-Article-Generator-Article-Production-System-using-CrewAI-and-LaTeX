from __future__ import annotations

import logging
import traceback
from multiprocessing import Process, Queue

from article_generator.constants import DEFAULT_AGENT_TIMEOUT_SECONDS
from article_generator.shared.ipc_models import AgentMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subprocess entry point (module-level so it is picklable on Windows/spawn)
# ---------------------------------------------------------------------------

def _agent_subprocess(
    agent_cls: type,
    task_description: str,
    expected_output: str,
    in_queue: Queue,
    out_queue: Queue,
    agent_name: str,
    llm_kwargs: dict,
) -> None:
    """Run inside the OS process: build agent, consume one message, produce one message."""
    try:
        from crewai import Crew, Task
        from crewai import Process as CrewProcess

        from article_generator.shared.llm_factory import build_llm

        # Block until the previous stage puts its AgentMessage into our queue.
        # Timeout=None → Watchdog handles the wall-clock limit by terminating us.
        in_msg: AgentMessage = in_queue.get(timeout=None)

        # Propagate upstream errors immediately without doing any LLM work.
        if in_msg.message_type == "error":
            out_queue.put(
                AgentMessage(
                    sender=agent_name,
                    recipient="",
                    content=in_msg.content,
                    topic=in_msg.topic,
                    message_type="error",
                )
            )
            return

        llm = build_llm(**llm_kwargs)
        agent = agent_cls(llm=llm).build()

        content_prefix = (
            f"CONTENT FROM PREVIOUS AGENT:\n\n{in_msg.content}\n\n---\n\n"
            if in_msg.content and in_msg.message_type == "output"
            else ""
        )
        task = Task(
            description=content_prefix + task_description.replace("{topic}", in_msg.topic),
            expected_output=expected_output,
            agent=agent,
        )
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=CrewProcess.sequential,
            verbose=False,
        )
        result = crew.kickoff()

        out_queue.put(
            AgentMessage(
                sender=agent_name,
                recipient="",           # GatekeeperRouter fills in the next recipient
                content=result.raw or "",
                topic=in_msg.topic,
                message_type="output",
            )
        )

    except Exception:
        out_queue.put(
            AgentMessage(
                sender=agent_name,
                recipient="orchestrator",
                content=traceback.format_exc(),
                topic="",
                message_type="error",
            )
        )
        raise


# ---------------------------------------------------------------------------
# AgentProcessRunner
# ---------------------------------------------------------------------------

class AgentProcessRunner:
    """Wraps a single CrewAI agent builder class in an isolated OS process.

    The agent, its LLM, and all tools are instantiated *inside* the subprocess —
    nothing non-picklable is passed across the process boundary.
    """

    def __init__(
        self,
        agent_cls: type,
        task_description: str,
        expected_output: str,
        in_queue: Queue,
        out_queue: Queue,
        agent_name: str = "",
        timeout: int = DEFAULT_AGENT_TIMEOUT_SECONDS,
        llm_kwargs: dict | None = None,
    ) -> None:
        self._agent_cls = agent_cls
        self._task_description = task_description
        self._expected_output = expected_output
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._agent_name = agent_name or agent_cls.__name__
        self._timeout = timeout
        self._llm_kwargs: dict = llm_kwargs or {}
        self._process: Process | None = None

    # ------------------------------------------------------------------
    # Public lifecycle methods
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn the OS process (agent is built inside, never pickled)."""
        self._process = Process(
            target=_agent_subprocess,
            args=(
                self._agent_cls,
                self._task_description,
                self._expected_output,
                self._in_queue,
                self._out_queue,
                self._agent_name,
                self._llm_kwargs,
            ),
            daemon=False,
            name=f"agent-{self._agent_name}",
        )
        self._process.start()
        logger.info("Spawned agent process '%s' (pid=%s)", self._agent_name, self._process.pid)

    def join(self, timeout: float | None = None) -> None:
        """Block until the subprocess exits (or timeout elapses)."""
        if self._process is not None:
            self._process.join(timeout=timeout)

    def terminate(self) -> None:
        """Send SIGTERM to the subprocess; used by Watchdog on timeout."""
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            logger.warning("Terminated agent process '%s' (pid=%s)", self._agent_name, self._process.pid)

    def is_alive(self) -> bool:
        """Return True if the subprocess is still running."""
        return self._process is not None and self._process.is_alive()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pid(self) -> int | None:
        """OS process ID, or None if not yet started."""
        return self._process.pid if self._process is not None else None

    @property
    def exitcode(self) -> int | None:
        """Exit code of the subprocess: 0 = normal, non-zero = crash, None = still running or not started."""
        return self._process.exitcode if self._process is not None else None

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @property
    def timeout(self) -> int:
        return self._timeout
