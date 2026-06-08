from __future__ import annotations

from crewai import Agent

from article_generator.constants import PROJECT_ROOT
from article_generator.services.tools.search_tools import build_search_tool

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "researcher")

_ROLE = "Senior Academic Researcher"
_GOAL = (
    "Conduct thorough internet research and compile accurate, well-sourced "
    "data and key facts on the article topic"
)
_BACKSTORY = (
    "You are a meticulous academic researcher with years of experience in "
    "literature reviews. You use search engines effectively to find credible "
    "sources, extract key facts, and organize information into structured "
    "outlines. You always cite your sources."
)


class ResearcherAgent:
    """Builds the ResearcherAgent — uses SerperDevTool for live internet search."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent configured with SerperDevTool and researcher skill."""
        kwargs: dict = {
            "role": _ROLE,
            "goal": _GOAL,
            "backstory": _BACKSTORY,
            "tools": [build_search_tool()],
            "skills": [_SKILLS_PATH],
            "verbose": self._verbose,
        }
        if self._llm is not None:
            kwargs["llm"] = self._llm
        return Agent(**kwargs)
