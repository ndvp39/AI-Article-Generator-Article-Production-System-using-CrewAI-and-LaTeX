from __future__ import annotations

from crewai import Agent

from article_generator.constants import PROJECT_ROOT

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "editor")

_ROLE = "Academic Reviewer and Quality Controller"
_GOAL = (
    "Check factual accuracy, improve text clarity and coherence, and ensure "
    "content quality — without changing the original meaning"
)
_BACKSTORY = (
    "You are a seasoned peer reviewer with a sharp eye for logical "
    "inconsistencies, unclear writing, and unsupported claims. You improve "
    "the text without rewriting it — you enhance clarity while preserving "
    "the author's intent."
)


class EditorAgent:
    """Builds the EditorAgent (Reviewer/QC) — no tools; reviews from context only."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent with no tools and editor skill."""
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
