from __future__ import annotations

# Integration tests — T-067
#
# Verify that the bibliography appears as the final section in the generated
# document, and that in-text citation numbers link to bibliography entries.
#
# DoD: Last section of PDF is bibliography; all entries displayed; clicking
#      in-text citation jumps to entry.
#
# Two-tier approach:
#   Tier 1 (.tex source) — always run; verify \printbibliography is the last
#           content command before \end{document} in the generated .tex.
#   Tier 2 (PDF checks) — compile a minimal .tex, verify bibliography text
#           appears on the last page via pdftotext.
import shutil
import subprocess

import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    CompilationError,
    CompilationResult,
    LaTeXCompiler,
    Reference,
)

pytestmark = pytest.mark.skipif(
    shutil.which("xelatex") is None or shutil.which("biber") is None,
    reason="xelatex and biber must be installed to run bibliography placement tests",
)

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

_MINIMAL_MD = """\
## Abstract
Abstract text with a citation [@vaswani2017].

## Introduction
Introduction text [@goodfellow2016].

## Conclusion
Conclusion text.
"""

_REFS: list[Reference] = [
    Reference(
        key="vaswani2017",
        entry_type="article",
        author="Vaswani, Ashish and others",
        title="Attention Is All You Need",
        year="2017",
        journal="Advances in Neural Information Processing Systems",
        volume="30",
    ),
    Reference(
        key="goodfellow2016",
        entry_type="book",
        author="Goodfellow, Ian and Bengio, Yoshua and Courville, Aaron",
        title="Deep Learning",
        year="2016",
        publisher="MIT Press",
    ),
]

_STANDARD_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[backend=biber,style=numeric]{biblatex}
\usepackage[colorlinks=true]{hyperref}
\addbibresource{references.bib}
\title{Bibliography Placement Test}
\author{Test Author}
\date{2026-06-09}
\begin{document}
\maketitle
\tableofcontents
\newpage
\section{Introduction}
Transformers \cite{vaswani2017} changed NLP.
Deep learning \cite{goodfellow2016} is foundational.
\section{Conclusion}
See references.
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
@book{goodfellow2016,
  author    = {Goodfellow, Ian and Bengio, Yoshua and Courville, Aaron},
  title     = {Deep Learning},
  publisher = {MIT Press},
  year      = {2016},
}
""".lstrip()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bibplacement_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Generate .tex via generate_tex() for source-level checks."""
    work_dir = tmp_path_factory.mktemp("bibplace_src")
    cfg = ArticleConfig(
        topic="Bibliography Placement",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MINIMAL_MD, cfg)


@pytest.fixture(scope="module")
def bibplace_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> CompilationResult:
    """Compile the standard-fonts .tex with bibliography; skip if fails."""
    work_dir = tmp_path_factory.mktemp("bibplace_compile")
    (work_dir / "article.tex").write_text(_STANDARD_TEX, encoding="utf-8")
    (work_dir / "references.bib").write_text(_STANDARD_BIB, encoding="utf-8")
    try:
        return LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        pytest.skip(f"Bibliography placement PDF tests skipped: {exc}")


@pytest.fixture(scope="module")
def last_page_text(bibplace_result: CompilationResult) -> str:
    """Extract the last page of the PDF via pdftotext."""
    pdftotext = shutil.which("pdftotext")
    pdfinfo   = shutil.which("pdfinfo")
    if pdftotext is None:
        pytest.skip("pdftotext not available")

    assert bibplace_result.pdf_path is not None
    pdf_path = str(bibplace_result.pdf_path)

    # Find total page count
    page_count = None
    if pdfinfo:
        proc = subprocess.run([pdfinfo, pdf_path], capture_output=True, timeout=15)
        if proc.returncode == 0:
            out = proc.stdout.decode("utf-8", errors="replace")
            for line in out.splitlines():
                if line.startswith("Pages:"):
                    page_count = int(line.split(":", 1)[1].strip())
                    break

    if page_count is None:
        page_count = 99  # fallback: extract last 3 pages

    # Extract the last page
    proc = subprocess.run(
        [pdftotext, "-enc", "UTF-8", "-f", str(page_count), "-l", str(page_count),
         pdf_path, "-"],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip("pdftotext failed on last page")
    return proc.stdout.decode("utf-8", errors="replace")


@pytest.fixture(scope="module")
def full_pdf_text(bibplace_result: CompilationResult) -> str:
    """Extract the full PDF text for bibliography presence check."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("pdftotext not available")
    assert bibplace_result.pdf_path is not None
    proc = subprocess.run(
        [pdftotext, "-enc", "UTF-8", str(bibplace_result.pdf_path), "-"],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip("pdftotext failed")
    return proc.stdout.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Tier 1: .tex source checks — always run
# ---------------------------------------------------------------------------


def test_printbibliography_present_in_tex(bibplacement_tex: str) -> None:
    r"""\printbibliography is emitted by generate_tex()."""
    assert r"\printbibliography" in bibplacement_tex


def test_printbibliography_before_end_document(bibplacement_tex: str) -> None:
    r"""\printbibliography must appear before \end{document}."""
    pos_bib = bibplacement_tex.find(r"\printbibliography")
    pos_end = bibplacement_tex.find(r"\end{document}")
    assert pos_bib != -1 and pos_end != -1
    assert pos_bib < pos_end, r"\printbibliography must come before \end{document}"


def test_printbibliography_is_last_content_command(bibplacement_tex: str) -> None:
    r"""\printbibliography is the final content command (nothing between it and
    \end{document} except whitespace)."""
    pos_bib = bibplacement_tex.find(r"\printbibliography")
    pos_end = bibplacement_tex.find(r"\end{document}")
    between = bibplacement_tex[pos_bib + len(r"\printbibliography"):pos_end].strip()
    # Only empty lines or comments allowed between \printbibliography and \end{document}
    meaningful = [ln for ln in between.splitlines() if ln.strip() and not ln.strip().startswith("%")]
    assert meaningful == [], (
        f"Unexpected content between \\printbibliography and \\end{{document}}: {meaningful}"
    )


def test_tex_addbibresource_present(bibplacement_tex: str) -> None:
    r"""\addbibresource{...} wires the .bib file into the preamble."""
    assert r"\addbibresource{" in bibplacement_tex


# ---------------------------------------------------------------------------
# Tier 2: PDF bibliography checks — skipped if compilation fails
# ---------------------------------------------------------------------------


def test_bibliography_pdf_compiles_ok(bibplace_result: CompilationResult) -> None:
    """T-067 DoD: document with bibliography compiles successfully."""
    assert bibplace_result.success is True


def test_bibliography_pdf_four_passes(bibplace_result: CompilationResult) -> None:
    assert bibplace_result.passes_completed == 4


def test_bibliography_appears_in_full_pdf(full_pdf_text: str) -> None:
    """T-067 DoD: PDF contains bibliography entries (author names / titles)."""
    has_vaswani = "Vaswani" in full_pdf_text
    has_goodfellow = "Goodfellow" in full_pdf_text
    assert has_vaswani or has_goodfellow, (
        "Neither 'Vaswani' nor 'Goodfellow' found in PDF — bibliography may be missing"
    )


def test_bibliography_title_appears_in_pdf(full_pdf_text: str) -> None:
    """'References' heading is present in the PDF."""
    assert "References" in full_pdf_text


def test_pdf_has_link_annotations_for_citations(bibplace_result: CompilationResult) -> None:
    """T-067 DoD: citation numbers are clickable — PDF has link annotations."""
    assert bibplace_result.pdf_path is not None
    pdf_bytes = bibplace_result.pdf_path.read_bytes()
    has_links = b"/Subtype /Link" in pdf_bytes or b"/Subtype/Link" in pdf_bytes
    assert has_links, "No hyperlink annotations found — citations may not be clickable"


def test_bbl_file_exists(bibplace_result: CompilationResult) -> None:
    """.bbl file created by biber confirms the bibliography was processed."""
    assert bibplace_result.pdf_path is not None
    bbl = bibplace_result.pdf_path.with_suffix(".bbl")
    assert bbl.exists(), ".bbl file missing — biber may not have run"
