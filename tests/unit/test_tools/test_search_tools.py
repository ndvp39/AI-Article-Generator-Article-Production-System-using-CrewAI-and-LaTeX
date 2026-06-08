from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.tools.search_tools import (
    RESEARCHER_ROLE,
    SEARCH_TOOLS,
    ToolIsolationError,
    build_search_tool,
    validate_tool_isolation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(role: str, tool_names: list[str]):
    agent = MagicMock()
    agent.role = role
    agent.tools = [_named_tool(n) for n in tool_names]
    return agent


def _named_tool(class_name: str):
    tool = MagicMock()
    type(tool).__name__ = class_name
    return tool


# ---------------------------------------------------------------------------
# build_search_tool
# ---------------------------------------------------------------------------

def test_build_search_tool_returns_serper_instance():
    with patch.dict("os.environ", {"SERPER_API_KEY": "test_key_123"}):
        with patch("article_generator.services.tools.search_tools.SerperDevTool") as MockTool:
            result = build_search_tool()
    MockTool.assert_called_once()
    assert result is MockTool.return_value


def test_build_search_tool_raises_when_key_missing():
    env = {k: v for k, v in __import__("os").environ.items() if k != "SERPER_API_KEY"}
    with patch.dict("os.environ", env, clear=True):
        with pytest.raises(EnvironmentError, match="SERPER_API_KEY environment variable not set"):
            build_search_tool()


def test_build_search_tool_raises_when_key_empty_string():
    with patch.dict("os.environ", {"SERPER_API_KEY": ""}):
        with pytest.raises(EnvironmentError):
            build_search_tool()


def test_build_search_tool_error_mentions_dotenv():
    env = {k: v for k, v in __import__("os").environ.items() if k != "SERPER_API_KEY"}
    with patch.dict("os.environ", env, clear=True):
        with pytest.raises(EnvironmentError, match=".env file"):
            build_search_tool()


# ---------------------------------------------------------------------------
# SEARCH_TOOLS constant
# ---------------------------------------------------------------------------

def test_search_tools_contains_serper():
    assert "SerperDevTool" in SEARCH_TOOLS


def test_search_tools_contains_website_and_duckduckgo():
    assert "WebsiteSearchTool" in SEARCH_TOOLS
    assert "DuckDuckGoSearchTool" in SEARCH_TOOLS


# ---------------------------------------------------------------------------
# validate_tool_isolation — valid configurations
# ---------------------------------------------------------------------------

def test_researcher_with_serper_does_not_raise():
    researcher = make_agent(RESEARCHER_ROLE, ["SerperDevTool"])
    validate_tool_isolation([researcher])  # no exception


def test_non_search_tools_on_other_agents_do_not_raise():
    agents = [
        make_agent(RESEARCHER_ROLE, ["SerperDevTool"]),
        make_agent("Senior Academic Writer", ["FileWriterTool"]),
        make_agent("Senior LaTeX Formatter", ["FileWriterTool"]),
        make_agent("BiDi Specialist", ["FileReadTool", "FileWriterTool"]),
        make_agent("Graph Generator", ["CodeInterpreterTool"]),
    ]
    validate_tool_isolation(agents)  # no exception


def test_empty_agent_list_does_not_raise():
    validate_tool_isolation([])


def test_agents_with_no_tools_do_not_raise():
    agents = [make_agent("Senior Academic Writer", []), make_agent("Editor", [])]
    validate_tool_isolation(agents)


# ---------------------------------------------------------------------------
# validate_tool_isolation — violations
# ---------------------------------------------------------------------------

def test_writer_with_serper_raises():
    agents = [
        make_agent(RESEARCHER_ROLE, ["SerperDevTool"]),
        make_agent("Senior Academic Writer", ["SerperDevTool"]),
    ]
    with pytest.raises(ToolIsolationError, match="Senior Academic Writer"):
        validate_tool_isolation(agents)


def test_website_search_tool_on_editor_raises():
    agents = [make_agent("Senior Academic Editor", ["WebsiteSearchTool"])]
    with pytest.raises(ToolIsolationError, match="WebsiteSearchTool"):
        validate_tool_isolation(agents)


def test_duckduckgo_on_formatter_raises():
    agents = [make_agent("LaTeX Formatter", ["DuckDuckGoSearchTool"])]
    with pytest.raises(ToolIsolationError):
        validate_tool_isolation(agents)


def test_multiple_violations_caught_on_first_offender():
    agents = [
        make_agent("WriterAgent", ["SerperDevTool"]),
        make_agent("EditorAgent", ["WebsiteSearchTool"]),
    ]
    with pytest.raises(ToolIsolationError):
        validate_tool_isolation(agents)


def test_violation_message_names_agent_role():
    agents = [make_agent("SomeRandomAgent", ["SerperDevTool"])]
    with pytest.raises(ToolIsolationError, match="SomeRandomAgent"):
        validate_tool_isolation(agents)
