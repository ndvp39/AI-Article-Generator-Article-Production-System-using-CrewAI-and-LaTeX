from __future__ import annotations

import re

from article_generator.services.latex_models import (
    _BIB_FIELD_ORDER,
    _INLINE_SUBS,
    _LATEX_ESCAPE_RE,
    _REQUIRED_BIB_FIELDS,
    _REQUIRED_SECTIONS,
    ArticleConfig,
    BibGenerationError,
    LaTeXGenerationError,
    Reference,
)


def validate_markdown(markdown: str) -> None:
    """Raise LaTeXGenerationError if required sections are absent."""
    lower = markdown.lower()
    missing = [
        s for s in _REQUIRED_SECTIONS
        if not re.search(rf"^#+\s+{re.escape(s)}", lower, re.MULTILINE)
    ]
    if missing:
        raise LaTeXGenerationError(f"Markdown is missing required sections: {missing}")


def validate_reference(ref: Reference) -> None:
    """Raise BibGenerationError if *ref* is missing required BibTeX fields."""
    required = _REQUIRED_BIB_FIELDS.get(ref.entry_type)
    if required is None:
        raise BibGenerationError(
            f"Reference '{ref.key}': unknown entry type '{ref.entry_type}'. "
            f"Supported types: {sorted(_REQUIRED_BIB_FIELDS)}"
        )
    missing = [f for f in required if not getattr(ref, f, "")]
    if missing:
        raise BibGenerationError(
            f"Reference '{ref.key}' (@{ref.entry_type}) missing fields: {missing}"
        )


def format_bib_entry(ref: Reference) -> str:
    """Return a single formatted BibTeX @entry string."""
    field_lines = [
        f"  {fname:<12} = {{{getattr(ref, fname, '')}}},"
        for fname in _BIB_FIELD_ORDER
        if getattr(ref, fname, "")
    ]
    return f"@{ref.entry_type}{{{ref.key},\n" + "\n".join(field_lines) + "\n}"


def build_document(body: str, config: ArticleConfig) -> str:
    """Assemble a complete LaTeX document string from *body* and *config*."""
    parts = [
        build_preamble(config), "",
        r"\begin{document}", "",
        r"\maketitle", r"\thispagestyle{empty}", "",
        r"\tableofcontents", r"\newpage", "",
        body, "",
        r"\printbibliography", "",
        r"\end{document}",
    ]
    return "\n".join(parts)


def build_preamble(config: ArticleConfig) -> str:
    """Return the LaTeX preamble string for *config*."""
    topic    = escape_tex(config.topic)
    author   = escape_tex(config.author)
    date     = escape_tex(config.date)
    course   = escape_tex(config.course)
    lecturer = escape_tex(config.lecturer)
    bib_file = config.paths.bib_filename
    lines = [
        r"\documentclass[12pt,a4paper]{article}", "",
        r"% Engine & language",
        r"\usepackage{polyglossia}",
        r"\setmainlanguage{hebrew}",
        r"\setotherlanguage{english}",
        r"\newfontfamily\hebrewfont[Script=Hebrew]{David CLM}", "",
        r"% Layout & structure",
        r"\usepackage[a4paper, margin=2.5cm]{geometry}",
        r"\usepackage{fancyhdr}",
        r"\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}",
        r"\usepackage{setspace}", "",
        r"% Mathematics",
        r"\usepackage{amsmath}", r"\usepackage{amssymb}", r"\usepackage{mathtools}", "",
        r"% Figures & tables",
        r"\usepackage{graphicx}", r"\usepackage{booktabs}",
        r"\usepackage{tabularx}", r"\usepackage{float}", "",
        r"\usepackage{tikz}", "",
        r"% Bibliography",
        r"\usepackage[backend=biber, style=numeric, sorting=nyt]{biblatex}",
        rf"\addbibresource{{{bib_file}}}", "",
        r"% Page style",
        r"\pagestyle{fancy}", r"\fancyhf{}",
        r"\fancyhead[R]{\leftmark}", r"\fancyfoot[C]{\thepage}",
        r"\renewcommand{\headrulewidth}{0.4pt}", "",
        r"% Document metadata",
        rf"\title{{\textbf{{{topic}}}\\[0.5em]\large {course}\\[0.3em]\normalsize {lecturer}}}",
        rf"\author{{{author}}}", rf"\date{{{date}}}",
    ]
    return "\n".join(lines)


def escape_tex(text: str) -> str:
    """Escape LaTeX special characters in plain config-field text."""
    return _LATEX_ESCAPE_RE.sub(r"\\\1", text)


def apply_inline(text: str) -> str:
    """Apply all inline Markdown → LaTeX substitutions to *text*."""
    for pattern, replacement in _INLINE_SUBS:
        text = pattern.sub(replacement, text)
    return text
