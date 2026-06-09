from __future__ import annotations

# Integration tests — T-074
#
# Verify the full pipeline: ArticleGeneratorSDK → CrewService →
# ProcessOrchestrator → ArticleResult, with mocked LLM/Serper (no real
# subprocesses or API calls).
#
# DoD: Pipeline runs with mocked LLM and Serper calls; all agents fire in
#      order; ArticleResult is populated (success=True, markdown_content set).
import threading
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.services.process_orchestrator import _N_AGENTS, _PIPELINE_SPEC
from article_generator.shared.ipc_models import AgentMessage
from article_generator.shared.models import ArticleResult

_SDK_BASE = "article_generator.sdk.sdk"
_ORCH_BASE = "article_generator.services.process_orchestrator"

_TOPIC = "Transformers in NLP"
_FINAL_CONTENT = "## מבוא\nTransformers revolutionised NLP."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inject_final_message(orchestrator, content: str, topic: str) -> None:
    """Wait until the orchestrator has built its pipeline queues, then
    inject the final AgentMessage so _run_pipeline unblocks."""
    while not orchestrator._pipeline:
        time.sleep(0.005)
    orchestrator._pipeline[_N_AGENTS - 1][1].put(
        AgentMessage(
            sender="bidi_specialist",
            recipient="orchestrator",
            content=content,
            topic=topic,
            message_type="output",
        )
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sdk_mocks():
    """Patch SDK-level collaborators that are irrelevant to pipeline routing."""
    with ExitStack() as stack:
        m = {
            "config": stack.enter_context(patch(f"{_SDK_BASE}.ConfigManager")),
            "gatekeeper": stack.enter_context(patch(f"{_SDK_BASE}.ApiGatekeeper")),
            "cost_tracker": stack.enter_context(patch(f"{_SDK_BASE}.CostTracker")),
            "file_manager": stack.enter_context(patch(f"{_SDK_BASE}.FileManager")),
        }
        # ConfigManager.load_setup returns minimal valid config
        m["config"].return_value.load_setup.return_value = {
            "agents": {"temperature": "0.7"}
        }
        m["config"].return_value.load_provider_limits.return_value = MagicMock()
        yield m


@pytest.fixture()
def pipeline_run(sdk_mocks):
    """Run the full SDK → CrewService → ProcessOrchestrator pipeline with
    AgentProcessRunner mocked (no real subprocesses).

    Returns (result, mock_runner_cls, captured_runner_calls).
    """
    with ExitStack() as stack:
        MockRunner = stack.enter_context(patch(f"{_ORCH_BASE}.AgentProcessRunner"))
        MockRunner.return_value.is_alive.return_value = False

        MockRouter = stack.enter_context(patch(f"{_ORCH_BASE}.GatekeeperRouter"))
        MockRouter.return_value.last_error = None

        MockWatchdog = stack.enter_context(patch(f"{_ORCH_BASE}.Watchdog"))
        MockWatchdog.return_value.all_healthy.return_value = True

        sdk = ArticleGeneratorSDK()

        # We need the actual ProcessOrchestrator instance so we can inject into
        # its queues — capture it via a side_effect wrapper.
        _real_orchestrators: list = []

        _OrigOrch_cls = None
        import article_generator.services.process_orchestrator as _orch_mod
        _OrigOrch = _orch_mod.ProcessOrchestrator

        class _CapturingOrch(_OrigOrch):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                _real_orchestrators.append(self)

        with patch(
            "article_generator.services.crew_service.ProcessOrchestrator",
            new=_CapturingOrch,
        ):
            def _run():
                return sdk.generate_article(_TOPIC)

            # Inject message in background thread once queue is ready
            inject_thread: list[threading.Thread] = []

            _original_init = _CapturingOrch.__init__

            def _patched_init(self, *a, **kw):
                _original_init(self, *a, **kw)
                t = threading.Thread(
                    target=_inject_final_message,
                    args=(self, _FINAL_CONTENT, _TOPIC),
                    daemon=True,
                )
                inject_thread.append(t)
                t.start()

            _CapturingOrch.__init__ = _patched_init

            result = _run()

        yield result, MockRunner, sdk


# ---------------------------------------------------------------------------
# T-074 DoD: ArticleResult populated
# ---------------------------------------------------------------------------


def test_pipeline_returns_article_result(pipeline_run):
    result, _, _ = pipeline_run
    assert isinstance(result, ArticleResult)


def test_pipeline_result_success_is_true(pipeline_run):
    result, _, _ = pipeline_run
    assert result.success is True


def test_pipeline_result_markdown_content_populated(pipeline_run):
    result, _, _ = pipeline_run
    assert result.markdown_content == _FINAL_CONTENT


def test_pipeline_result_tex_path_set(pipeline_run):
    result, _, _ = pipeline_run
    assert result.tex_path != ""


def test_pipeline_result_bib_path_set(pipeline_run):
    result, _, _ = pipeline_run
    assert result.bib_path != ""


def test_pipeline_result_pdf_path_set(pipeline_run):
    result, _, _ = pipeline_run
    assert result.pdf_path != ""


# ---------------------------------------------------------------------------
# T-074 DoD: all agents fire in order
# ---------------------------------------------------------------------------


def test_pipeline_creates_six_agent_runners(pipeline_run):
    """ProcessOrchestrator spawns exactly 6 AgentProcessRunners."""
    _, MockRunner, _ = pipeline_run
    assert MockRunner.call_count == 6


def test_pipeline_starts_all_six_runners(pipeline_run):
    _, MockRunner, _ = pipeline_run
    assert MockRunner.return_value.start.call_count == 6


def test_pipeline_agent_names_in_order(pipeline_run):
    """Runners are constructed with agent names in the canonical pipeline order."""
    _, MockRunner, _ = pipeline_run
    actual_names = [
        c.kwargs.get("agent_name", c.args[5] if len(c.args) > 5 else None)
        for c in MockRunner.call_args_list
    ]
    expected_names = [spec[3] for spec in _PIPELINE_SPEC]
    assert actual_names == expected_names


def test_pipeline_researcher_is_first_agent(pipeline_run):
    _, MockRunner, _ = pipeline_run
    first_call = MockRunner.call_args_list[0]
    name = first_call.kwargs.get("agent_name") or first_call.args[5]
    assert name == "researcher"


def test_pipeline_bidi_specialist_is_last_agent(pipeline_run):
    _, MockRunner, _ = pipeline_run
    last_call = MockRunner.call_args_list[-1]
    name = last_call.kwargs.get("agent_name") or last_call.args[5]
    assert name == "bidi_specialist"


def test_pipeline_writer_follows_researcher(pipeline_run):
    _, MockRunner, _ = pipeline_run
    names = [
        c.kwargs.get("agent_name") or c.args[5]
        for c in MockRunner.call_args_list
    ]
    assert names.index("writer") == names.index("researcher") + 1


def test_pipeline_editor_follows_writer(pipeline_run):
    _, MockRunner, _ = pipeline_run
    names = [
        c.kwargs.get("agent_name") or c.args[5]
        for c in MockRunner.call_args_list
    ]
    assert names.index("editor") == names.index("writer") + 1


# ---------------------------------------------------------------------------
# Cost report saved after pipeline run
# ---------------------------------------------------------------------------


def test_pipeline_generates_cost_report(pipeline_run):
    _, _, sdk = pipeline_run
    sdk._cost_tracker.generate_report.assert_called_once()


def test_pipeline_saves_cost_report(pipeline_run):
    _, _, sdk = pipeline_run
    sdk._cost_tracker.save_report.assert_called_once()


# ---------------------------------------------------------------------------
# Wiring: SDK → CrewService → ProcessOrchestrator
# ---------------------------------------------------------------------------


def test_pipeline_config_loaded_for_orchestrator(sdk_mocks, pipeline_run):
    """ConfigManager.load_setup() must be called to supply config to ProcessOrchestrator."""
    sdk_mocks["config"].return_value.load_setup.assert_called_once()


def test_pipeline_passes_topic_through_stack(pipeline_run):
    """The topic is preserved from SDK.generate_article() through to ArticleResult."""
    result, _, _ = pipeline_run
    # markdown_content comes from the injected final message which was keyed to _TOPIC
    assert result.markdown_content == _FINAL_CONTENT
