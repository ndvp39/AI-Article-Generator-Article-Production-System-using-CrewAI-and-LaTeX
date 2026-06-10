from __future__ import annotations

from crewai import Agent, Task

from article_generator.services.tasks.task_prompts import (
    _BIDI_DESC,
    _BIDI_OUT,
    _GRAPH_DESC,
    _GRAPH_OUT,
    _LATEX_DESC,
    _LATEX_OUT,
    _RESEARCH_DESC,
    _RESEARCH_OUT,
    _REVIEW_DESC,
    _REVIEW_OUT,
    _WRITE_DESC,
    _WRITE_OUT,
)

__all__ = [
    "build_tasks",
    "_RESEARCH_DESC", "_RESEARCH_OUT",
    "_WRITE_DESC", "_WRITE_OUT",
    "_REVIEW_DESC", "_REVIEW_OUT",
    "_GRAPH_DESC", "_GRAPH_OUT",
    "_LATEX_DESC", "_LATEX_OUT",
    "_BIDI_DESC", "_BIDI_OUT",
]


def build_tasks(
    researcher: Agent,
    writer: Agent,
    editor: Agent,
    graph_generator: Agent,
    latex_formatter: Agent,
    bidi_specialist: Agent,
    topic: str,
) -> list[Task]:
    """Create all 6 pipeline tasks with context chaining and return them in order."""
    research_task = Task(
        description=_RESEARCH_DESC.format(topic=topic),
        expected_output=_RESEARCH_OUT,
        agent=researcher,
    )
    write_task = Task(
        description=_WRITE_DESC.format(topic=topic),
        expected_output=_WRITE_OUT,
        agent=writer,
        context=[research_task],
    )
    review_task = Task(
        description=_REVIEW_DESC,
        expected_output=_REVIEW_OUT,
        agent=editor,
        context=[write_task],
    )
    graph_task = Task(
        description=_GRAPH_DESC,
        expected_output=_GRAPH_OUT,
        agent=graph_generator,
        context=[review_task],
    )
    latex_task = Task(
        description=_LATEX_DESC,
        expected_output=_LATEX_OUT,
        agent=latex_formatter,
        context=[review_task],
    )
    bidi_task = Task(
        description=_BIDI_DESC,
        expected_output=_BIDI_OUT,
        agent=bidi_specialist,
        context=[latex_task],
    )
    return [research_task, write_task, review_task, graph_task, latex_task, bidi_task]
