"""Task prompt strings for all 6 pipeline agents."""
from __future__ import annotations

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
    "Using ONLY the researcher's outline as your source, write a complete academic "
    "article in Markdown on: '{topic}'.\n"
    "LANGUAGE REQUIREMENT (non-negotiable): The article body MUST be written primarily "
    "in Hebrew (≥ 90% of prose). English is permitted ONLY for: technical terms, "
    "variable names, code snippets, and citations. All section titles, abstracts, "
    "introductions, chapter bodies, and conclusions MUST be in Hebrew.\n"
    "LENGTH REQUIREMENT: The article must be ≥ 12,000 words to produce ≥ 15 PDF pages. "
    "Every chapter must be substantial (≥ 2,000 words each). Do NOT truncate.\n"
    "Must include: cover metadata block, abstract (Hebrew), introduction (Hebrew), "
    "≥ 4 body chapters in Hebrew, ≥ 1 Markdown table, "
    "≥ 1 formula placeholder (<!-- FORMULA: ... -->), "
    "≥ 1 graph placeholder ([GRAPH: ...]), conclusion (Hebrew), "
    "and bibliography list. All citations must use [AuthorYear] format."
)
_WRITE_OUT = (
    "Complete Markdown article (≥ 12,000 words, ≥ 15 pages when compiled) written "
    "primarily in Hebrew (≥ 90% prose in Hebrew). Contains all mandatory sections: "
    "abstract, introduction, ≥ 4 chapters, conclusion, bibliography — all in Hebrew. "
    "Includes ≥ 1 table, ≥ 1 formula placeholder, ≥ 1 graph placeholder, "
    "and all citations in [AuthorYear] format."
)

_REVIEW_DESC = (
    "Review and improve the writer's Markdown article. Fix plain-text formula words "
    "(e.g. 'sigma' → '$\\sigma$', 'integral' → '$\\int$'). Remove weak language "
    "('very', 'basically', 'obviously'). Improve clarity and academic tone. "
    "IMPORTANT: Do NOT translate Hebrew to English — the article must remain primarily "
    "in Hebrew (≥ 90% Hebrew prose). If content was accidentally shortened, restore it "
    "to the full ≥ 12,000-word length. "
    "Do NOT remove or alter [AuthorYear] citations, tables, formula placeholders, "
    "graph placeholders, Hebrew text, or any structural section."
)
_REVIEW_OUT = (
    "Revised Markdown article with improved academic tone and clarity. "
    "Still primarily in Hebrew (≥ 90% prose). Full length maintained (≥ 12,000 words). "
    "All structural elements preserved: table, formula placeholders, graph "
    "placeholder, Hebrew content, and all [AuthorYear] citations intact."
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
    "Convert the reviewed Markdown article into a complete XeLaTeX .tex document "
    "with Hebrew as the MAIN language and English as secondary.\n"
    "PREAMBLE (non-negotiable package order): fontspec, polyglossia "
    "(\\setmainlanguage{hebrew}, \\setotherlanguage{english}), geometry, "
    "fancyhdr, graphicx, amsmath+amssymb, booktabs+tabularx, tikz, biblatex, "
    "hyperref, bidi (bidi MUST be last).\n"
    "CONTENT RULES: Hebrew body text goes directly in the document. Wrap any "
    "English paragraphs in \\begin{english}...\\end{english}. Inline English "
    "technical terms use \\LR{...}. Math inside Hebrew text must use \\LR{$...$}.\n"
    "Replace formula placeholders with real LaTeX math environments (equation/align). "
    "Embed graph via \\includegraphics{figures/graph.pdf}. "
    "Convert [AuthorYear] → \\cite{authoryear}. End with \\printbibliography.\n"
    "OUTPUT: Write the COMPLETE .tex file to results/article.tex via FileWriterTool. "
    "Then output ONLY a short confirmation message (file path + byte count). "
    "Do NOT output the LaTeX content itself — only write it to disk."
)
_LATEX_OUT = (
    "Confirmation message: 'Written results/article.tex — N bytes'. "
    "The file at results/article.tex contains the complete XeLaTeX document with: "
    "\\setmainlanguage{hebrew}, title page, \\tableofcontents, fancyhdr headers/footers, "
    "≥ 1 equation environment, ≥ 1 tabularx table, \\includegraphics for graph, "
    "Hebrew body text, \\cite{} commands, and \\printbibliography as final element."
)

_BIDI_DESC = (
    "Read results/article.tex via FileReadTool. Inspect the document for BiDi issues:\n"
    "1. Verify \\setmainlanguage{hebrew} and \\setotherlanguage{english} are present.\n"
    "2. Find any bare Hebrew text outside proper language environments.\n"
    "3. Find any unguarded inline math ($...$) inside Hebrew text — wrap with \\LR{$...$}.\n"
    "4. Find tables inside RTL blocks — move outside or wrap with \\begin{english}.\n"
    "5. Verify bidi package is loaded LAST in the preamble (after hyperref).\n"
    "Fix all issues found. Write the COMPLETE corrected file back to results/article.tex "
    "via FileWriterTool. Then output ONLY a short report — do NOT output the LaTeX content "
    "itself. Report format: 'BiDi fix complete: N issues found, N fixed. "
    "results/article.tex updated.'"
)
_BIDI_OUT = (
    "Short confirmation report: 'BiDi fix complete: N issues found, N fixed. "
    "results/article.tex updated.' "
    "The corrected file at results/article.tex has: \\setmainlanguage{hebrew}, "
    "all Hebrew text in correct language context, inline math wrapped with \\LR{}, "
    "and bidi loaded last."
)
