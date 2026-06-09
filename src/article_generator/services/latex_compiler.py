from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from article_generator.constants import ARTICLE_TEX_FILE, ASSETS_DIR, RESULTS_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArticlePaths:
    output_dir: Path = field(default_factory=lambda: RESULTS_DIR)
    assets_dir: Path = field(default_factory=lambda: ASSETS_DIR)
    bib_filename: str = "references.bib"


@dataclass
class ArticleConfig:
    topic: str
    author: str
    date: str
    course: str
    lecturer: str
    paths: ArticlePaths = field(default_factory=ArticlePaths)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LaTeXGenerationError(Exception):
    """Raised when generate_tex() cannot produce valid output."""


class BibGenerationError(Exception):
    """Raised when generate_bib() finds a reference with missing required fields."""


class CompilationError(Exception):
    """Raised when a LaTeX compilation pass produces fatal errors."""


class CompilationTimeoutError(CompilationError):
    """Raised when a compilation subprocess exceeds its timeout."""


# ---------------------------------------------------------------------------
# Inline conversion patterns  (applied left-to-right, order matters)
# ---------------------------------------------------------------------------

# Citation  [@key]  →  \cite{key}   — must run before generic link pattern
_RE_CITE = re.compile(r"\[@([\w:._-]+)\]")
# Hyperlink  [text](url)  →  \href{url}{text}
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# Bold  **text**  →  \textbf{text}
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
# Italic  *text*  →  \textit{text}  (after bold so ** is already consumed)
_RE_ITALIC = re.compile(r"\*(.+?)\*")
# Inline code  `code`  →  \texttt{code}
_RE_CODE = re.compile(r"`([^`]+)`")

_INLINE_SUBS: list[tuple[re.Pattern[str], str]] = [
    (_RE_CITE,   r"\\cite{\1}"),
    (_RE_LINK,   r"\\href{\2}{\1}"),
    (_RE_BOLD,   r"\\textbf{\1}"),
    (_RE_ITALIC, r"\\textit{\1}"),
    (_RE_CODE,   r"\\texttt{\1}"),
]

# Characters that need escaping in plain-text config fields
_LATEX_ESCAPE_RE = re.compile(r"([%&_#\$])")

# Required section keywords (lowercase); checked against headings
_REQUIRED_SECTIONS = ("abstract", "introduction", "conclusion")


# ---------------------------------------------------------------------------
# LaTeXCompiler
# ---------------------------------------------------------------------------


class LaTeXCompiler:
    """Produces a complete .tex source file from a Markdown article.

    T-054: generate_tex()   — Markdown → .tex with full preamble.
    T-055: generate_bib()   — reference list → .bib file (stub).
    T-056: compile()        — 4-pass LuaLaTeX + biber compilation (stub).
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        assets_dir: Path | None = None,
    ) -> None:
        self._output_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
        self._assets_dir = Path(assets_dir) if assets_dir is not None else ASSETS_DIR

    # ------------------------------------------------------------------
    # T-054  Public API: generate_tex
    # ------------------------------------------------------------------

    def generate_tex(self, markdown: str, config: ArticleConfig) -> str:
        """Convert *markdown* to a complete LaTeX document and write it to disk.

        Raises:
            LaTeXGenerationError: if required sections (Abstract, Introduction,
                                  Conclusion) are missing from *markdown*.
        """
        self._validate_markdown(markdown)
        body = self._convert_body(markdown)
        tex = self._build_document(body, config)

        output_path = Path(config.paths.output_dir) / ARTICLE_TEX_FILE
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tex, encoding="utf-8")
        logger.info("LaTeXCompiler: wrote %s (%d bytes)", output_path, len(tex.encode()))
        return tex

    # ------------------------------------------------------------------
    # T-055 stub: generate_bib (implemented in T-055)
    # ------------------------------------------------------------------

    def generate_bib(self, references: list, config: ArticleConfig) -> str:  # type: ignore[type-arg]
        raise NotImplementedError("generate_bib() will be implemented in T-055")

    # ------------------------------------------------------------------
    # T-056 stub: compile (implemented in T-056)
    # ------------------------------------------------------------------

    def compile(self, tex_path: str, bib_path: str) -> object:
        raise NotImplementedError("compile() will be implemented in T-056")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_markdown(self, markdown: str) -> None:
        lower = markdown.lower()
        missing = [
            s for s in _REQUIRED_SECTIONS
            if not re.search(rf"^#+\s+{re.escape(s)}", lower, re.MULTILINE)
        ]
        if missing:
            raise LaTeXGenerationError(
                f"Markdown is missing required sections: {missing}"
            )

    # ------------------------------------------------------------------
    # Document assembly
    # ------------------------------------------------------------------

    def _build_document(self, body: str, config: ArticleConfig) -> str:
        parts = [
            self._build_preamble(config),
            "",
            r"\begin{document}",
            "",
            r"\maketitle",
            r"\thispagestyle{empty}",
            "",
            r"\tableofcontents",
            r"\newpage",
            "",
            body,
            "",
            r"\printbibliography",
            "",
            r"\end{document}",
        ]
        return "\n".join(parts)

    def _build_preamble(self, config: ArticleConfig) -> str:
        topic    = self._escape_tex(config.topic)
        author   = self._escape_tex(config.author)
        date     = self._escape_tex(config.date)
        course   = self._escape_tex(config.course)
        lecturer = self._escape_tex(config.lecturer)
        bib_file = config.paths.bib_filename

        lines = [
            r"\documentclass[12pt,a4paper]{article}",
            "",
            r"% Engine & language",
            r"\usepackage{polyglossia}",
            r"\setmainlanguage{hebrew}",
            r"\setotherlanguage{english}",
            r"\newfontfamily\hebrewfont[Script=Hebrew]{David CLM}",
            "",
            r"% Layout & structure",
            r"\usepackage[a4paper, margin=2.5cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}",
            r"\usepackage{setspace}",
            "",
            r"% Mathematics",
            r"\usepackage{amsmath}",
            r"\usepackage{amssymb}",
            r"\usepackage{mathtools}",
            "",
            r"% Figures & tables",
            r"\usepackage{graphicx}",
            r"\usepackage{booktabs}",
            r"\usepackage{tabularx}",
            r"\usepackage{float}",
            "",
            r"% Graphics / diagrams",
            r"\usepackage{tikz}",
            "",
            r"% Bibliography",
            r"\usepackage[backend=biber, style=numeric, sorting=nyt]{biblatex}",
            rf"\addbibresource{{{bib_file}}}",
            "",
            r"% Page style",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\fancyhead[R]{\leftmark}",
            r"\fancyfoot[C]{\thepage}",
            r"\renewcommand{\headrulewidth}{0.4pt}",
            "",
            r"% Document metadata",
            rf"\title{{\textbf{{{topic}}}\\[0.5em]\large {course}\\[0.3em]\normalsize {lecturer}}}",
            rf"\author{{{author}}}",
            rf"\date{{{date}}}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Markdown → LaTeX body
    # ------------------------------------------------------------------

    def _convert_body(self, markdown: str) -> str:
        lines = markdown.splitlines()
        output: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Formula directive: <!-- FORMULA: <content> -->
            formula_match = re.match(r"<!--\s*FORMULA:\s*(.*?)\s*-->", stripped)
            if formula_match:
                output.append(r"\begin{equation}")
                output.append(f"    {formula_match.group(1)}")
                output.append(r"\end{equation}")
                i += 1
                continue

            # Table block: collect consecutive pipe lines
            if stripped.startswith("|"):
                table_lines: list[str] = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                output.append(self._table_to_tabularx(table_lines))
                continue

            # Headings — check h3 before h2 before h1 to avoid prefix overlap
            m = re.match(r"^(#{1,3})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                title = self._apply_inline(m.group(2))
                cmd = {1: r"\section", 2: r"\subsection", 3: r"\subsubsection"}[level]
                output.append(rf"{cmd}{{{title}}}")
                i += 1
                continue

            # Standalone image: ![alt](path)
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if img_match:
                output.append(self._image_to_figure(img_match.group(2), img_match.group(1)))
                i += 1
                continue

            # Blank line
            if not stripped:
                output.append("")
                i += 1
                continue

            # Regular text / paragraph line
            output.append(self._apply_inline(line))
            i += 1

        return "\n".join(output)

    # ------------------------------------------------------------------
    # Table conversion
    # ------------------------------------------------------------------

    def _table_to_tabularx(self, rows: list[str]) -> str:
        if len(rows) < 3:
            return ""

        header_cells = self._parse_row(rows[0])
        n_cols = len(header_cells)
        # Last column expands; all others left-aligned
        col_spec = "l" * (n_cols - 1) + "X" if n_cols > 1 else "X"

        header_row = "  " + " & ".join(
            rf"\textbf{{{self._apply_inline(c)}}}" for c in header_cells
        ) + r" \\"

        data_rows: list[str] = []
        for row in rows[2:]:          # rows[1] is the separator
            cells = self._parse_row(row)
            while len(cells) < n_cols:
                cells.append("")
            cells = cells[:n_cols]
            data_rows.append("  " + " & ".join(self._apply_inline(c) for c in cells) + r" \\")

        return "\n".join([
            r"\begin{table}[htbp]",
            r"  \centering",
            rf"  \begin{{tabularx}}{{\textwidth}}{{{col_spec}}}",
            r"  \toprule",
            header_row,
            r"  \midrule",
            *data_rows,
            r"  \bottomrule",
            r"  \end{tabularx}",
            r"\end{table}",
        ])

    @staticmethod
    def _parse_row(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip().strip("|").split("|")]

    # ------------------------------------------------------------------
    # Image → figure environment
    # ------------------------------------------------------------------

    @staticmethod
    def _image_to_figure(path: str, alt: str) -> str:
        latex_path = path.replace("\\", "/")
        label = re.sub(r"[^a-zA-Z0-9]", "_", alt.lower()) or "fig"
        caption = alt or "Figure"
        return "\n".join([
            r"\begin{figure}[htbp]",
            r"  \centering",
            rf"  \includegraphics[width=0.85\textwidth]{{{latex_path}}}",
            rf"  \caption{{{caption}}}",
            rf"  \label{{fig:{label}}}",
            r"\end{figure}",
        ])

    # ------------------------------------------------------------------
    # Inline substitutions
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_inline(text: str) -> str:
        for pattern, replacement in _INLINE_SUBS:
            text = pattern.sub(replacement, text)
        return text

    @staticmethod
    def _escape_tex(text: str) -> str:
        """Escape LaTeX special characters in plain config-field text."""
        return _LATEX_ESCAPE_RE.sub(r"\\\1", text)
