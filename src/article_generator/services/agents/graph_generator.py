from __future__ import annotations

from crewai import Agent

from article_generator.constants import PROJECT_ROOT
from article_generator.services.tools.code_interpreter_tool import LocalCodeInterpreterTool

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "graph_generator")

_ROLE = "Data Visualization Specialist"
_GOAL = (
    "Produce clean, executable Python code that generates a meaningful data "
    "visualization relevant to the article topic"
)
_BACKSTORY = (
    "You are a Python data visualization expert who specialises in matplotlib "
    "and seaborn. You write self-contained, headless-safe graph code that saves "
    "figures to disk without displaying them. You always validate and execute "
    "your code locally before submitting it."
)


class GraphGeneratorAgent:
    """Builds the GraphGeneratorAgent — uses LocalCodeInterpreterTool for self-verification."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent with LocalCodeInterpreterTool and graph_generator skill."""
        kwargs: dict = {
            "role": _ROLE,
            "goal": _GOAL,
            "backstory": _BACKSTORY,
            "tools": [LocalCodeInterpreterTool()],
            "skills": [_SKILLS_PATH],
            "verbose": self._verbose,
        }
        if self._llm is not None:
            kwargs["llm"] = self._llm
        return Agent(**kwargs)
