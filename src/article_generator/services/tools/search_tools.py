from __future__ import annotations

import logging
import os
from typing import Any

from crewai_tools import SerperDevTool

logger = logging.getLogger(__name__)

SEARCH_TOOLS = {"SerperDevTool", "WebsiteSearchTool", "DuckDuckGoSearchTool"}
RESEARCHER_ROLE = "Senior Academic Researcher"


class ToolIsolationError(Exception):
    pass


def build_search_tool() -> SerperDevTool:
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        raise OSError(
            "SERPER_API_KEY environment variable not set. "
            "Add it to your .env file."
        )
    logger.info("SerperDevTool initialised (key present)")
    return SerperDevTool()


def validate_tool_isolation(agents: list[Any]) -> None:
    for agent in agents:
        if agent.role == RESEARCHER_ROLE:
            continue
        tool_names = {type(t).__name__ for t in agent.tools}
        violations = tool_names & SEARCH_TOOLS
        if violations:
            raise ToolIsolationError(
                f"Agent '{agent.role}' has internet search tool(s) "
                f"{violations} — only ResearcherAgent may have search tools."
            )
