from __future__ import annotations

from crewai import Agent
from crewai_tools import FileReadTool, FileWriterTool

from article_generator.constants import PROJECT_ROOT

_SKILLS_PATH = str(PROJECT_ROOT / "skills" / "bidi_specialist")

_ROLE = "Hebrew–English Bidirectional Text Specialist"
_GOAL = (
    "Validate and correct all Hebrew–English direction switching in the .tex "
    "file; fix any formulas degraded to plain text due to BiDi confusion"
)
_BACKSTORY = (
    "You are an expert in Hebrew–English bidirectional LaTeX typesetting. "
    "You understand the bidi, polyglossia, and hyperref package interaction "
    "rules, and you correct direction issues with surgical precision without "
    "altering the article's content."
)


class BiDiSpecialistAgent:
    """Builds the BiDiSpecialistAgent — reads and writes .tex via file tools."""

    def __init__(self, llm: object | None = None, verbose: bool = False) -> None:
        self._llm = llm
        self._verbose = verbose

    def build(self) -> Agent:
        """Return a crewai.Agent with FileReadTool + FileWriterTool and bidi skill."""
        kwargs: dict = {
            "role": _ROLE,
            "goal": _GOAL,
            "backstory": _BACKSTORY,
            "tools": [FileReadTool(), FileWriterTool()],
            "skills": [_SKILLS_PATH],
            "verbose": self._verbose,
        }
        if self._llm is not None:
            kwargs["llm"] = self._llm
        return Agent(**kwargs)
