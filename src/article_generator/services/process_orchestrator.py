from __future__ import annotations

import logging
import queue as queue_module
from multiprocessing import Queue

import article_generator.services.tasks.task_definitions as _td
from article_generator.constants import (
    AGENT_TIMEOUT_SECONDS,
    ARTICLE_PDF_FILE,
    ARTICLE_TEX_FILE,
    DEFAULT_AGENT_TIMEOUT_SECONDS,
    REFERENCES_BIB_FILE,
    RESULTS_DIR,
)
from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent
from article_generator.services.agents.editor import EditorAgent
from article_generator.services.agents.graph_generator import GraphGeneratorAgent
from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent
from article_generator.services.agents.researcher import ResearcherAgent
from article_generator.services.agents.writer import WriterAgent
from article_generator.services.gatekeeper_router import GatekeeperRouter
from article_generator.services.watchdog import Watchdog
from article_generator.shared.ipc_models import AgentMessage
from article_generator.shared.models import ArticleResult
from article_generator.shared.process_runner import AgentProcessRunner

logger = logging.getLogger(__name__)

# Pipeline specification: (agent_cls, task_description, expected_output, agent_name)
# Order must match sequential pipeline execution.
_PIPELINE_SPEC: list[tuple[type, str, str, str]] = [
    (ResearcherAgent,     _td._RESEARCH_DESC, _td._RESEARCH_OUT, "researcher"),
    (WriterAgent,         _td._WRITE_DESC,    _td._WRITE_OUT,    "writer"),
    (EditorAgent,         _td._REVIEW_DESC,   _td._REVIEW_OUT,   "editor"),
    (GraphGeneratorAgent, _td._GRAPH_DESC,    _td._GRAPH_OUT,    "graph_generator"),
    (LaTeXFormatterAgent, _td._LATEX_DESC,    _td._LATEX_OUT,    "latex_formatter"),
    (BiDiSpecialistAgent, _td._BIDI_DESC,     _td._BIDI_OUT,     "bidi_specialist"),
]

_N_AGENTS = len(_PIPELINE_SPEC)


class ProcessOrchestrator:
    """Creates and coordinates 6 isolated agent OS processes.

    Pipeline flow:
        orchestrator → Q_in[0] → [Researcher] → Q_out[0]
                                                    ↓ GatekeeperRouter
                               Q_in[1] → [Writer] → Q_out[1]  ...
                                                    ↓ GatekeeperRouter
                         Q_in[5] → [BiDiSpec] → Q_out[5] → orchestrator
    """

    def __init__(self, config: dict, llm_kwargs: dict | None = None) -> None:
        temperature = float(config.get("agents", {}).get("temperature", 0.7))
        self._llm_kwargs: dict = llm_kwargs or {"temperature": temperature}
        self._pipeline: list[tuple[Queue, Queue]] = []
        self._runners: list[AgentProcessRunner] = []
        self._router: GatekeeperRouter | None = None
        self._watchdog: Watchdog | None = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, topic: str) -> ArticleResult:
        """Run the full multi-process pipeline; return ArticleResult."""
        logger.info("ProcessOrchestrator starting pipeline — topic: %s", topic)
        try:
            return self._run_pipeline(topic)
        except Exception:
            logger.exception("ProcessOrchestrator encountered an error; shutting down")
            self._shutdown()
            raise

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------

    def _run_pipeline(self, topic: str) -> ArticleResult:
        # 1. Create 6 (Q_in, Q_out) pairs
        self._pipeline = [(Queue(), Queue()) for _ in range(_N_AGENTS)]

        # 2. Build AgentProcessRunners
        self._runners = [
            AgentProcessRunner(
                agent_cls=agent_cls,
                task_description=task_desc,
                expected_output=expected_out,
                in_queue=self._pipeline[i][0],
                out_queue=self._pipeline[i][1],
                agent_name=agent_name,
                timeout=AGENT_TIMEOUT_SECONDS.get(agent_name, DEFAULT_AGENT_TIMEOUT_SECONDS),
                llm_kwargs=self._llm_kwargs,
            )
            for i, (agent_cls, task_desc, expected_out, agent_name) in enumerate(_PIPELINE_SPEC)
        ]

        # 3. Spawn all agent processes
        for runner in self._runners:
            runner.start()
            logger.info("Spawned %s (pid=%s)", runner.agent_name, runner.pid)

        # 4. Start GatekeeperRouter + Watchdog as daemon threads
        agent_names = [r.agent_name for r in self._runners]
        self._router = GatekeeperRouter(pipeline=self._pipeline, agent_names=agent_names)
        self._router.start()

        self._watchdog = Watchdog(runners=self._runners)
        self._watchdog.start()

        # 5. Inject the initial AgentMessage into researcher's input queue
        self._pipeline[0][0].put(
            AgentMessage(
                sender="orchestrator",
                recipient="researcher",
                content=topic,
                topic=topic,
                message_type="input",
            )
        )
        logger.info("Initial message injected for researcher")

        # 6. Block on final output from bidi specialist's output queue
        total_timeout = (
            sum(AGENT_TIMEOUT_SECONDS.get(n, DEFAULT_AGENT_TIMEOUT_SECONDS) for n in agent_names)
            + 60  # buffer
        )
        try:
            final_msg: AgentMessage = self._pipeline[_N_AGENTS - 1][1].get(
                timeout=total_timeout
            )
        except queue_module.Empty:
            self._raise_pipeline_error("timed out waiting for final output")

        # 7. Shutdown cleanly
        self._shutdown()

        # 8. Surface any downstream errors
        if final_msg.message_type == "error":
            raise RuntimeError(
                f"Pipeline failed in agent '{final_msg.sender}': "
                f"{final_msg.content[:300]}"
            )
        if self._router and self._router.last_error:
            raise RuntimeError(
                f"GatekeeperRouter validation error: {self._router.last_error}"
            )
        if self._watchdog and not self._watchdog.all_healthy():
            raise RuntimeError(
                "Pipeline failed: one or more agents crashed or timed out"
            )

        logger.info("ProcessOrchestrator pipeline complete")
        return ArticleResult(
            success=True,
            markdown_content=final_msg.content,
            tex_path=str(RESULTS_DIR / ARTICLE_TEX_FILE),
            bib_path=str(RESULTS_DIR / REFERENCES_BIB_FILE),
            pdf_path=str(RESULTS_DIR / ARTICLE_PDF_FILE),
        )

    def _shutdown(self) -> None:
        """Stop daemon threads and join / terminate all agent processes."""
        if self._router is not None:
            self._router.stop()
        if self._watchdog is not None:
            self._watchdog.stop()
        for runner in self._runners:
            runner.join(timeout=5.0)
            if runner.is_alive():
                runner.terminate()
        logger.info("ProcessOrchestrator shutdown complete")

    def _raise_pipeline_error(self, reason: str) -> None:
        self._shutdown()
        raise RuntimeError(f"Pipeline error: {reason}")
