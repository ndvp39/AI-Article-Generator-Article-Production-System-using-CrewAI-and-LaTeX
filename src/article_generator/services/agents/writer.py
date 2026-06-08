from __future__ import annotations

from crewai import Agent

from article_generator.constants import PROJECT_ROOT

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "writer")

_ROLE = "Academic Article Writer"
_GOAL = (
    "Transform the research outline into a complete, well-structured, "
    "~15-page academic article in Markdown format"
)
_BACKSTORY = (
    "You are an experienced academic writer who excels at transforming raw "
    "research notes into clear, engaging scholarly articles. You write in both "
    "Hebrew and English, understand academic structure, and produce clean "
    "Markdown that converts well to LaTeX."
)


class WriterAgent:
    """Builds the WriterAgent — no internet search tool; writes from context only."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent with no tools and writer skill."""
        kwargs: dict = {
            "role": _ROLE,
            "goal": _GOAL,
            "backstory": _BACKSTORY,
            "tools": [],
            "skills": [_SKILLS_PATH],
            "verbose": self._verbose,
        }
        if self._llm is not None:
            kwargs["llm"] = self._llm
        return Agent(**kwargs)
