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
    "Using ONLY the researcher's outline, write a complete academic article in Markdown "
    "on: '{topic}'.\n\n"
    "LANGUAGE: ≥ 90%% Hebrew prose. English only for technical terms, variable names, "
    "code snippets, and citations. All headings, body text, and conclusions in Hebrew.\n\n"
    "MANDATORY SECTIONS — write ALL in order (missing or truncated section = TASK FAILURE):\n"
    "  1. Cover block (Hebrew): title, author name, date, "
    "course name (AI Agents — MSC Course HW3), lecturer (Dr. Yoram Segal)\n"
    "  2. ## Abstract — ≥ 400 Hebrew words\n"
    "  3. ## Introduction — ≥ 1,000 Hebrew words\n"
    "  4. ## Chapter 1 [title from outline] — ≥ 1,200 Hebrew words\n"
    "  5. ## Chapter 2 [title from outline] — ≥ 1,200 Hebrew words\n"
    "  6. ## Chapter 3 [title from outline] — ≥ 1,200 Hebrew words\n"
    "  7. ## Chapter 4 [title from outline] — ≥ 1,200 Hebrew words\n"
    "  8. ## Conclusion — ≥ 600 Hebrew words\n"
    "  9. ## Bibliography — every reference from the outline in [AuthorYear] format\n\n"
    "VISUAL ELEMENTS (embed inside chapters):\n"
    "  - ≥ 1 Markdown table: | col | col | format\n"
    "  - ≥ 1 formula placeholder: <!-- FORMULA: describe the formula -->\n"
    "  - ≥ 1 graph placeholder: [GRAPH: describe the graph]\n\n"
    "ANTI-TRUNCATION RULE: Write every section to its FULL minimum length before moving "
    "to the next. Do NOT write '[continued]', '[truncated]', '[see full version]', or any "
    "placeholder text in place of real content. If you are running low on space, write "
    "shorter but COMPLETE paragraphs — every section must appear in full. "
    "Total article MUST reach ≥ 8,000 Hebrew words. Output the entire article now."
)
_WRITE_OUT = (
    "Complete Markdown article (≥ 8,000 Hebrew words, ≥ 15 pages when compiled). "
    "All 9 sections present and fully written in Hebrew (≥ 90%% prose). "
    "Includes ≥ 1 table, ≥ 1 formula placeholder, ≥ 1 graph placeholder, "
    "and all citations in [AuthorYear] format. No truncated or placeholder sections."
)

_REVIEW_DESC = (
    "Review and improve the writer's Markdown article. Fix plain-text formula words "
    "(e.g. 'sigma' → '$\\sigma$', 'integral' → '$\\int$'). Remove weak language "
    "('very', 'basically', 'obviously'). Improve clarity and academic tone. "
    "IMPORTANT: Do NOT translate Hebrew to English — the article must remain primarily "
    "in Hebrew (≥ 90% Hebrew prose). If content was accidentally shortened, restore it "
    "to the full ≥ 8,000-word length. "
    "Do NOT remove or alter [AuthorYear] citations, tables, formula placeholders, "
    "graph placeholders, Hebrew text, or any structural section."
)
_REVIEW_OUT = (
    "Revised Markdown article with improved academic tone and clarity. "
    "Still primarily in Hebrew (≥ 90% prose). Full length maintained (≥ 8,000 words). "
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
    "FONTS (non-negotiable — use exactly these, they are installed on the system): "
    "\\setmainfont{Times New Roman}, \\setsansfont{Arial}, \\setmonofont{Courier New}, "
    "\\newfontfamily\\hebrewfont{Arial}[Script=Hebrew]. "
    "Do NOT use FreeSerif, FreeFont, Linux Libertine, or any other font.\n"
    "PREAMBLE (non-negotiable package order): fontspec (with fonts above), polyglossia "
    "(\\setmainlanguage{hebrew}, \\setotherlanguage{english}), geometry, "
    "fancyhdr, graphicx, amsmath+amssymb, booktabs+tabularx, tikz, biblatex, "
    "hyperref, bidi (bidi MUST be last).\n"
    "CONTENT RULES: Hebrew body text goes directly in the document. Wrap any "
    "English paragraphs in \\begin{english}...\\end{english}. Inline English "
    "technical terms use \\LR{...}. Math inside Hebrew text must use \\LR{$...$}.\n"
    "Replace formula placeholders with real LaTeX math environments (equation/align). "
    "Embed graph via \\includegraphics{figures/graph.pdf}. "
    "Convert [AuthorYear] → \\cite{authoryear}. End with \\printbibliography.\n"
    "BODY DIRECTION: Immediately after \\end{titlepage}, insert \\setLR — "
    "this prevents 199 RTL↔LTR context switches from corrupting the layout. "
    "Without it, English text appears on the wrong side of the page.\n"
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
    "Read results/article.tex via FileReadTool. Inspect the document for BiDi structural "
    "markup issues ONLY. DO NOT add, inject, create, or translate any article content. "
    "The article language (Hebrew, English, or mixed) was set by the writer — preserve it exactly.\n"
    "Check only:\n"
    "1. Bare Hebrew text that is present but outside proper language environments — wrap it.\n"
    "2. Unguarded inline math ($...$) inside existing Hebrew text — wrap with \\LR{$...$}.\n"
    "3. Tables inside existing RTL blocks — move outside or wrap with \\begin{english}.\n"
    "4. Verify bidi package order in preamble (bidi LAST, after hyperref) if bidi is present.\n"
    "DO NOT add \\setmainlanguage, \\begin{hebrew}, or any language declaration that is not "
    "already in the document.\n"
    "Fix all issues found. Write the COMPLETE corrected file back to results/article.tex "
    "via FileWriterTool. Then output ONLY a short report — do NOT output the LaTeX content "
    "itself. Report format: 'BiDi fix complete: N issues found, N fixed. "
    "results/article.tex updated.'"
)
_BIDI_OUT = (
    "Short confirmation report: 'BiDi fix complete: N issues found, N fixed. "
    "results/article.tex updated.' "
    "The corrected file preserves the article's original language structure exactly. "
    "Only BiDi structural markup was adjusted; no content was added or translated."
)
