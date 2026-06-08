from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.agents.bidi_specialist import BiDiSpecialistAgent
from article_generator.services.agents.editor import EditorAgent
from article_generator.services.agents.graph_generator import GraphGeneratorAgent
from article_generator.services.agents.latex_formatter import LaTeXFormatterAgent
from article_generator.services.agents.researcher import ResearcherAgent
from article_generator.services.agents.writer import WriterAgent
from article_generator.services.crew_service import CrewService
from article_generator.shared.models import ArticleResult

_BASE = "article_generator.services.crew_service"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(temperature: str = "0.7") -> MagicMock:
    cfg = MagicMock()
    cfg.load_setup.return_value = {"agents": {"temperature": temperature}}
    return cfg


def _make_result(**kwargs) -> ArticleResult:
    defaults = {
        "success": True,
        "markdown_content": "article body",
        "tex_path": "results/article.tex",
        "bib_path": "results/references.bib",
        "pdf_path": "results/article.pdf",
    }
    defaults.update(kwargs)
    return ArticleResult(**defaults)


# ---------------------------------------------------------------------------
# Fixture — patches ProcessOrchestrator at the crew_service module level
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_orch():
    with patch(f"{_BASE}.ProcessOrchestrator") as MockOrch:
        MockOrch.return_value.run.return_value = _make_result()
        yield MockOrch


# ---------------------------------------------------------------------------
# run_pipeline — delegation to ProcessOrchestrator
# ---------------------------------------------------------------------------

def test_run_pipeline_returns_article_result(mock_orch):
    result = CrewService(_make_cfg()).run_pipeline("ML")
    assert isinstance(result, ArticleResult)


def test_run_pipeline_success_is_true(mock_orch):
    result = CrewService(_make_cfg()).run_pipeline("ML")
    assert result.success is True


def test_run_pipeline_loads_config_once(mock_orch):
    cfg = _make_cfg()
    CrewService(cfg).run_pipeline("topic")
    cfg.load_setup.assert_called_once()


def test_run_pipeline_passes_setup_dict_to_orchestrator(mock_orch):
    cfg = _make_cfg("0.5")
    CrewService(cfg).run_pipeline("topic")
    mock_orch.assert_called_once_with(config={"agents": {"temperature": "0.5"}})


def test_run_pipeline_passes_topic_to_orchestrator_run(mock_orch):
    CrewService(_make_cfg()).run_pipeline("quantum computing")
    mock_orch.return_value.run.assert_called_once_with("quantum computing")


def test_run_pipeline_returns_orchestrator_result_unchanged(mock_orch):
    expected = _make_result(markdown_content="generated content")
    mock_orch.return_value.run.return_value = expected
    result = CrewService(_make_cfg()).run_pipeline("topic")
    assert result is expected


def test_run_pipeline_creates_exactly_one_orchestrator(mock_orch):
    CrewService(_make_cfg()).run_pipeline("topic")
    mock_orch.assert_called_once()


def test_run_pipeline_calls_orchestrator_run_exactly_once(mock_orch):
    CrewService(_make_cfg()).run_pipeline("topic")
    mock_orch.return_value.run.assert_called_once()


def test_run_pipeline_no_direct_crewai_imports():
    """Confirm Crew and kickoff are not referenced in the module."""
    import inspect

    import article_generator.services.crew_service as mod
    src = inspect.getsource(mod)
    assert "kickoff" not in src
    assert "from crewai" not in src


# ---------------------------------------------------------------------------
# _build_agents — returns class references, not instances
# ---------------------------------------------------------------------------

def test_build_agents_returns_all_six_keys():
    result = CrewService(_make_cfg())._build_agents()
    assert set(result.keys()) == {
        "researcher",
        "writer",
        "editor",
        "graph_generator",
        "latex_formatter",
        "bidi_specialist",
    }


def test_build_agents_values_are_classes_not_instances():
    result = CrewService(_make_cfg())._build_agents()
    for key, val in result.items():
        assert isinstance(val, type), f"'{key}' should be a class, got {type(val)}"


def test_build_agents_researcher_is_researcher_agent_class():
    assert CrewService(_make_cfg())._build_agents()["researcher"] is ResearcherAgent


def test_build_agents_writer_is_writer_agent_class():
    assert CrewService(_make_cfg())._build_agents()["writer"] is WriterAgent


def test_build_agents_editor_is_editor_agent_class():
    assert CrewService(_make_cfg())._build_agents()["editor"] is EditorAgent


def test_build_agents_graph_generator_is_correct_class():
    assert CrewService(_make_cfg())._build_agents()["graph_generator"] is GraphGeneratorAgent


def test_build_agents_latex_formatter_is_correct_class():
    assert CrewService(_make_cfg())._build_agents()["latex_formatter"] is LaTeXFormatterAgent


def test_build_agents_bidi_specialist_is_correct_class():
    assert CrewService(_make_cfg())._build_agents()["bidi_specialist"] is BiDiSpecialistAgent
