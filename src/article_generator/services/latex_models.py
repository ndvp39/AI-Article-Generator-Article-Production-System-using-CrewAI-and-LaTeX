from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from article_generator.constants import ASSETS_DIR, REFERENCES_BIB_FILE, RESULTS_DIR

# ---------------------------------------------------------------------------
# Config & result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArticlePaths:
    output_dir: Path = field(default_factory=lambda: RESULTS_DIR)
    assets_dir: Path = field(default_factory=lambda: ASSETS_DIR)
    bib_filename: str = REFERENCES_BIB_FILE


@dataclass
class Reference:
    """One bibliographic reference for BibTeX output.

    *entry_type* must be one of: article, book, inproceedings, misc.
    Leave unused optional fields as empty strings (the default).
    """

    key: str
    entry_type: str
    author: str
    title: str
    year: str
    journal: str = ""
    volume: str = ""
    booktitle: str = ""
    publisher: str = ""
    number: str = ""
    pages: str = ""
    url: str = ""
    doi: str = ""
    note: str = ""


@dataclass
class ArticleConfig:
    topic: str
    author: str
    date: str
    course: str
    lecturer: str
    paths: ArticlePaths = field(default_factory=ArticlePaths)


@dataclass
class CompilationResult:
    """Outcome of a 4-pass LuaLaTeX + biber compilation run."""

    success: bool
    passes_completed: int
    pdf_path: Path | None
    errors: list[str]
    warnings: list[str]
    log_path: Path | None
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LaTeXGenerationError(Exception):
    """Raised when generate_tex() cannot produce valid output."""


class BibGenerationError(Exception):
    """Raised when generate_bib() finds a reference with missing required fields."""


class CompilationError(Exception):
    """Raised when a LaTeX compilation pass produces fatal errors."""

    def __init__(self, message: str, result: CompilationResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class CompilationTimeoutError(CompilationError):
    """Raised when a compilation subprocess exceeds its timeout."""


# ---------------------------------------------------------------------------
# Inline conversion patterns (applied left-to-right)
# ---------------------------------------------------------------------------

_RE_CITE = re.compile(r"\[@([\w:._-]+)\]")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC = re.compile(r"\*(.+?)\*")
_RE_CODE = re.compile(r"`([^`]+)`")

_INLINE_SUBS: list[tuple[re.Pattern[str], str]] = [
    (_RE_CITE,   r"\\cite{\1}"),
    (_RE_LINK,   r"\\href{\2}{\1}"),
    (_RE_BOLD,   r"\\textbf{\1}"),
    (_RE_ITALIC, r"\\textit{\1}"),
    (_RE_CODE,   r"\\texttt{\1}"),
]

_LATEX_ESCAPE_RE = re.compile(r"([%&_#\$])")
_REQUIRED_SECTIONS = ("abstract", "introduction", "conclusion")

_REQUIRED_BIB_FIELDS: dict[str, tuple[str, ...]] = {
    "article":       ("author", "title", "journal", "year", "volume"),
    "book":          ("author", "title", "publisher", "year"),
    "inproceedings": ("author", "title", "booktitle", "year"),
    "misc":          ("author", "title", "year", "url"),
}

_BIB_FIELD_ORDER = (
    "author", "title", "journal", "booktitle", "publisher",
    "year", "volume", "number", "pages", "url", "doi", "note",
)

_WARNING_PATTERNS = (
    r"Overfull \hbox",
    "undefined on input line",
    "Package hyperref Warning",
)
