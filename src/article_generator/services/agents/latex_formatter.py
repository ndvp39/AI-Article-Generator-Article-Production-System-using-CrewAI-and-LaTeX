from __future__ import annotations

from crewai import Agent
from crewai_tools import FileWriterTool

from article_generator.constants import PROJECT_ROOT

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "latex_formatter")

_ROLE = "LaTeX Typesetting Specialist"
_GOAL = (
    "Convert the approved Markdown article into complete, compilable LaTeX "
    "code ready for LuaLaTeX compilation"
)
_BACKSTORY = (
    "You are a LaTeX expert who specialises in academic typesetting, "
    "Hebrew–English bidirectional documents, and complex mathematical notation. "
    "You produce .tex files that compile on the first attempt and always load "
    "packages in the correct order."
)


class LaTeXFormatterAgent:
    """Builds the LaTeXFormatterAgent — writes .tex to disk via FileWriterTool."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent with FileWriterTool and latex_formatter skill."""
        kwargs: dict = {
            "role": _ROLE,
            "goal": _GOAL,
            "backstory": _BACKSTORY,
            "tools": [FileWriterTool()],
            "skills": [_SKILLS_PATH],
            "verbose": self._verbose,
        }
        if self._llm is not None:
            kwargs["llm"] = self._llm
        return Agent(**kwargs)
