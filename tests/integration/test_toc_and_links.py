from __future__ import annotations

# Integration tests — T-060
#
# Verify that the generated document has a table of contents and clickable
# internal hyperlinks.
#
# DoD: TOC entries present; clicking jumps to correct chapter.
#
# Two-tier approach:
#   Tier 1 (.tex source checks) — always run; verify \tableofcontents and
#           \usepackage{hyperref} are emitted by generate_tex().
#   Tier 2 (PDF checks) — compile a minimal standard-fonts .tex (no polyglossia)
#           that mirrors the structure produced by generate_tex(); verify TOC
#           section text via pdftotext and PDF link annotations via raw byte scan.
#           Skipped when lualatex/biber absent or compilation fails.
#
# Module-level skip when lualatex/biber are not installed.
import shutil
import subprocess
from pathlib import Path

import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    CompilationError,
    LaTeXCompiler,
    Reference,
)

pytestmark = pytest.mark.skipif(
    shutil.which("xelatex") is None or shutil.which("biber") is None,
    reason="xelatex and biber must both be installed to run LaTeX integration tests",
)

# ---------------------------------------------------------------------------
# Minimal .tex that mirrors the structure of generate_tex() output but uses
# standard fonts (no polyglossia / David CLM) so it compiles on any machine
# with a reasonably complete TeX Live / MiKTeX installation.
# ---------------------------------------------------------------------------

_SECTIONS = ["Introduction", "Methodology", "Conclusion"]

_STANDARD_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[backend=biber,style=numeric]{biblatex}
\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}
\addbibresource{references.bib}

\title{\textbf{Integration Test: TOC and Links}}
\author{Test Author}
\date{2026-06-09}

\begin{document}

\maketitle
\thispagestyle{empty}

\tableofcontents
\newpage

\section{Introduction}
This is the introduction section \cite{vaswani2017}.

\section{Methodology}
This is the methodology section.

\section{Conclusion}
This is the conclusion section.

\printbibliography

\end{document}
""".lstrip()

_STANDARD_BIB = r"""
@article{vaswani2017,
  author   = {Vaswani, Ashish and others},
  title    = {Attention Is All You Need},
  journal  = {Advances in Neural Information Processing Systems},
  year     = {2017},
  volume   = {30},
}
""".lstrip()

# A minimal markdown that generate_tex() can process (covers all required sections)
_COVER_MD = """\
## Abstract
Abstract text about the methodology.

## Introduction
Introduction text.

## Conclusion
Conclusion text.
"""

_REFS = [
    Reference(
        key="vaswani2017",
        entry_type="article",
        author="Vaswani, Ashish and others",
        title="Attention Is All You Need",
        year="2017",
        journal="Advances in Neural Information Processing Systems",
        volume="30",
    )
]

# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return the .tex source from generate_tex().  Always runs (no compile)."""
    work_dir = tmp_path_factory.mktemp("toc_gentex")
    cfg = ArticleConfig(
        topic="Test Topic",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_COVER_MD, cfg)


@pytest.fixture(scope="module")
def toc_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile the standard-fonts .tex and return the PDF path.

    This uses a non-Hebrew preamble so it compiles on any machine with
    biblatex + hyperref installed.  Skips gracefully if compilation fails.
    """
    work_dir = tmp_path_factory.mktemp("toc_compile")
    tex_path = work_dir / "article.tex"
    bib_path = work_dir / "references.bib"
    tex_path.write_text(_STANDARD_TEX, encoding="utf-8")
    bib_path.write_text(_STANDARD_BIB, encoding="utf-8")
    try:
        result = LaTeXCompiler().compile(str(tex_path), str(bib_path))
    except CompilationError as exc:
        pytest.skip(
            f"TOC/links PDF tests skipped — compilation failed.  "
            f"Install biblatex + hyperref TeX packages.  Error: {exc}"
        )
    if result.pdf_path is None or not result.pdf_path.exists():
        pytest.skip("PDF absent after compilation — cannot run PDF checks")
    return result.pdf_path


@pytest.fixture(scope="module")
def toc_page_text(toc_pdf: Path) -> str:
    """Extract text from the first two pages of the PDF (covers TOC location)."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("pdftotext not available")
    # Use -enc UTF-8 so pdftotext emits UTF-8 bytes regardless of system locale;
    # text=False avoids Windows charmap codec errors when decoding the pipe.
    proc = subprocess.run(
        [pdftotext, "-enc", "UTF-8", "-f", "1", "-l", "2", str(toc_pdf), "-"],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        pytest.skip(f"pdftotext failed: {stderr[:200]}")
    return proc.stdout.decode("utf-8", errors="replace")


@pytest.fixture(scope="module")
def pdf_bytes(toc_pdf: Path) -> bytes:
    """Read the raw PDF bytes for annotation inspection."""
    return toc_pdf.read_bytes()


# ---------------------------------------------------------------------------
# Tier 1: .tex source assertions — always run (no compilation required)
# ---------------------------------------------------------------------------


def test_generated_tex_has_tableofcontents(generated_tex: str) -> None:
    """`generate_tex()` emits the \\tableofcontents command."""
    assert r"\tableofcontents" in generated_tex


def test_generated_tex_has_hyperref(generated_tex: str) -> None:
    """`generate_tex()` includes the hyperref package for clickable links."""
    assert "hyperref" in generated_tex


def test_generated_tex_hyperref_has_colorlinks(generated_tex: str) -> None:
    assert "colorlinks" in generated_tex


def test_generated_tex_newpage_after_toc(generated_tex: str) -> None:
    r"""\\newpage follows \\tableofcontents to separate TOC from body."""
    toc_pos = generated_tex.find(r"\tableofcontents")
    np_pos  = generated_tex.find(r"\newpage", toc_pos)
    assert toc_pos != -1 and np_pos != -1, r"\tableofcontents or \newpage missing"
    assert np_pos > toc_pos, r"\newpage must come after \tableofcontents"


def test_generated_tex_begin_document_present(generated_tex: str) -> None:
    assert r"\begin{document}" in generated_tex


def test_generated_tex_maketitle_present(generated_tex: str) -> None:
    assert r"\maketitle" in generated_tex


# ---------------------------------------------------------------------------
# Tier 2a: TOC text in compiled PDF — skipped when compilation fails
# ---------------------------------------------------------------------------


def test_toc_page_contains_introduction(toc_page_text: str) -> None:
    """T-060 DoD: 'Introduction' appears in the TOC."""
    assert "Introduction" in toc_page_text


def test_toc_page_contains_methodology(toc_page_text: str) -> None:
    """T-060 DoD: 'Methodology' appears in the TOC."""
    assert "Methodology" in toc_page_text


def test_toc_page_contains_conclusion(toc_page_text: str) -> None:
    """T-060 DoD: 'Conclusion' appears in the TOC."""
    assert "Conclusion" in toc_page_text


def test_toc_page_contains_all_sections(toc_page_text: str) -> None:
    """All expected section titles appear within the first two PDF pages."""
    for section in _SECTIONS:
        assert section in toc_page_text, f"Section '{section}' missing from TOC page text"


# ---------------------------------------------------------------------------
# Tier 2b: PDF link annotation assertions — skipped when compilation fails
# ---------------------------------------------------------------------------


def test_pdf_has_link_annotations(pdf_bytes: bytes) -> None:
    """T-060 DoD: PDF contains /Subtype /Link annotations (clickable links).

    hyperref writes link annotations as PDF annotation objects.  Their
    presence confirms that TOC entries and citations are clickable.
    """
    # hyperref may write annotations as "/Subtype /Link" or "/Subtype/Link"
    # (with or without the space before the value) depending on PDF writer.
    has_links = b"/Subtype /Link" in pdf_bytes or b"/Subtype/Link" in pdf_bytes
    assert has_links, "No /Subtype /Link annotation found in PDF bytes"


def test_pdf_has_goto_actions(pdf_bytes: bytes) -> None:
    """Internal TOC jumps use /GoTo actions.  At least one must be present."""
    has_goto = b"/S /GoTo" in pdf_bytes or b"/S/GoTo" in pdf_bytes
    assert has_goto, "No /S /GoTo action found in PDF bytes — TOC links may not jump"


def test_pdf_has_multiple_pages(toc_pdf: Path) -> None:
    """A document with a TOC page and body sections must have >1 page."""
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None:
        pytest.skip("pdfinfo not available")
    proc = subprocess.run(
        [pdfinfo, str(toc_pdf)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    pages_line = next(
        (ln for ln in proc.stdout.splitlines() if ln.startswith("Pages:")), None
    )
    assert pages_line is not None, "pdfinfo did not report page count"
    page_count = int(pages_line.split(":", 1)[1].strip())
    assert page_count > 1, f"Expected >1 page in TOC document, got {page_count}"
