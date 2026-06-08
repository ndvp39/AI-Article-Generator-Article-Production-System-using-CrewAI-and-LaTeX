from __future__ import annotations

from crewai import Agent, Task

_RESEARCH_DESC = (
    "Research the topic: '{topic}'.\n"
    "Use SerperDevTool to run ≥ 3 distinct Google searches covering different "
    "aspects of the topic. Extract ≥ 5 credible references (author, title, year, "
    "URL). Organise findings into a structured outline: suggested title, chapter "
    "descriptions with key facts, and full reference list in [AuthorYear] format."
)
_RESEARCH_OUT = (
    "Structured research outline with: suggested article title, ≥ 4 chapter "
    "descriptions with key facts, and ≥ 5 references each with author, title, "
    "year, and URL in [AuthorYear] citation format."
)

_WRITE_DESC = (
    "Using ONLY the researcher's outline as your source, write a complete ~15-page "
    "academic article in Markdown on: '{topic}'.\n"
    "Must include: cover metadata block, abstract, introduction, ≥ 4 body chapters, "
    "≥ 1 Markdown table, ≥ 1 formula placeholder (<!-- FORMULA: ... -->), "
    "≥ 1 graph placeholder ([GRAPH: ...]), ≥ 1 Hebrew section, conclusion, "
    "and bibliography list. All citations must use [AuthorYear] format."
)
_WRITE_OUT = (
    "Complete Markdown article (~15 pages) containing all mandatory sections: "
    "abstract, introduction, ≥ 4 chapters, conclusion, bibliography. "
    "Includes ≥ 1 table, ≥ 1 formula placeholder, ≥ 1 graph placeholder, "
    "≥ 1 Hebrew section, and all citations in [AuthorYear] format."
)

_REVIEW_DESC = (
    "Review and improve the writer's Markdown article. Fix plain-text formula words "
    "(e.g. 'sigma' → '$\\sigma$', 'integral' → '$\\int$'). Remove weak language "
    "('very', 'basically', 'obviously'). Improve clarity and academic tone. "
    "Do NOT remove or alter [AuthorYear] citations, tables, formula placeholders, "
    "graph placeholders, Hebrew sections, or any structural section."
)
_REVIEW_OUT = (
    "Revised Markdown article with improved academic tone and clarity. "
    "All structural elements preserved: table, formula placeholders, graph "
    "placeholder, Hebrew section, and all [AuthorYear] citations intact."
)

_GRAPH_DESC = (
    "Write self-contained Python matplotlib code that generates a data visualisation "
    "relevant to the article topic. Required: matplotlib.use('Agg') as first line; "
    "plt.savefig('figures/graph.pdf'); axis labels and title; no plt.show(). "
    "Use LocalCodeInterpreterTool to execute the code and confirm it produces "
    "figures/graph.pdf with EXIT CODE: 0 before delivering."
)
_GRAPH_OUT = (
    "Verified executable Python matplotlib code that runs without errors and "
    "produces figures/graph.pdf. Code is self-contained, uses Agg backend, "
    "includes axis labels and a descriptive title relevant to the article topic."
)

_LATEX_DESC = (
    "Convert the reviewed Markdown article into a complete LuaLaTeX .tex document. "
    "Preamble package order (non-negotiable): fontspec, polyglossia, geometry, "
    "fancyhdr, graphicx, amsmath+amssymb, booktabs+tabularx, tikz, biblatex, "
    "hyperref, bidi (bidi MUST be last). Replace formula placeholders with real "
    "LaTeX math environments (equation/align). Embed graph via "
    "\\includegraphics{figures/graph.pdf}. Convert [AuthorYear] → \\cite{authoryear}. "
    "End with \\printbibliography. Write to results/article.tex via FileWriterTool."
)
_LATEX_OUT = (
    "Complete .tex file at results/article.tex with: title page, "
    "\\tableofcontents, fancyhdr headers/footers, ≥ 1 equation environment, "
    "≥ 1 tabularx table, \\includegraphics for graph, \\begin{hebrew} block, "
    "\\cite{} commands, and \\printbibliography as final element."
)

_BIDI_DESC = (
    "Read results/article.tex via FileReadTool. Run BiDiScanner to identify all "
    "BiDi issues: bare Hebrew outside \\begin{hebrew}, unguarded inline math "
    "inside hebrew environments, and tables inside RTL blocks. Fix each issue. "
    "Run BiDiScanner again to confirm the result is []. "
    "Write the corrected file back to results/article.tex via FileWriterTool."
)
_BIDI_OUT = (
    "Corrected results/article.tex where BiDiScanner returns []. "
    "Fix report: N issues found, N fixed, validation PASSED. "
    "At least one \\begin{hebrew} block present with correct RTL content."
)


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
