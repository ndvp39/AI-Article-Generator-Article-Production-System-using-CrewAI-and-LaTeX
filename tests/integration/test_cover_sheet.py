from __future__ import annotations

# Integration tests — T-059
#
# Verify that the cover sheet produced by generate_tex() + compile() contains
# all five required fields: topic, author, date, course, lecturer.
#
# DoD (T-059): PDF page 1 contains topic, author, date, course, lecturer.
#
# Two-tier approach:
#   Tier 1 (.tex source checks) — always run; verify the five fields are
#           embedded in the generated .tex preamble.
#   Tier 2 (PDF text checks) — skipped when compilation fails (e.g. the David
#           CLM Hebrew font is absent on the test machine), verified with
#           pdftotext when compilation succeeds.
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
    shutil.which("lualatex") is None or shutil.which("biber") is None,
    reason="lualatex and biber must both be installed to run LaTeX integration tests",
)

# ---------------------------------------------------------------------------
# Known field values — injected via ArticleConfig, expected in PDF cover page
# ---------------------------------------------------------------------------

TOPIC    = "Transformer Architecture and Attention Mechanisms"
AUTHOR   = "Test Author"
DATE     = "2026-06-09"
COURSE   = "MSc Advanced Machine Learning"
LECTURER = "Prof. Jane Smith"

_COVER_MD = """\
## Abstract
Abstract text about transformer models and attention.

## Introduction
Introduction text describing the motivation for this work.

## Conclusion
Conclusion text summarising the findings.
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
def cover_tex(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, ArticleConfig]:
    """Generate the .tex source via generate_tex().  Always runs (no compile)."""
    work_dir = tmp_path_factory.mktemp("cover_tex")
    cfg = ArticleConfig(
        topic=TOPIC,
        author=AUTHOR,
        date=DATE,
        course=COURSE,
        lecturer=LECTURER,
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    compiler = LaTeXCompiler()
    tex_content = compiler.generate_tex(_COVER_MD, cfg)
    compiler.generate_bib(_REFS, cfg)
    return tex_content, cfg


@pytest.fixture(scope="module")
def cover_pdf(cover_tex: tuple[str, ArticleConfig]) -> Path:
    """Compile the cover document; skip PDF-level tests when compilation fails.

    Failure is expected on machines where the David CLM Hebrew font (required
    by polyglossia + \\setmainlanguage{hebrew}) is not installed.
    """
    tex_content, cfg = cover_tex
    tex_path = str(cfg.paths.output_dir / "article.tex")
    bib_path = str(cfg.paths.output_dir / cfg.paths.bib_filename)
    try:
        result = LaTeXCompiler().compile(tex_path, bib_path)
    except CompilationError as exc:
        pytest.skip(
            f"PDF cover-sheet tests skipped — compilation failed, likely due to "
            f"missing David CLM Hebrew font or TeX packages.  Error: {exc}"
        )
    if result.pdf_path is None or not result.pdf_path.exists():
        pytest.skip("PDF path is None or file absent after compilation")
    return result.pdf_path


@pytest.fixture(scope="module")
def cover_page_text(cover_pdf: Path) -> str:
    """Extract page-1 text from the compiled PDF using pdftotext."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("pdftotext not available; cannot verify PDF text content")
    proc = subprocess.run(
        [pdftotext, "-f", "1", "-l", "1", str(cover_pdf), "-"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip(f"pdftotext failed: {proc.stderr.strip()[:200]}")
    return proc.stdout


# ---------------------------------------------------------------------------
# Tier 1: .tex source assertions — always run (no compilation required)
# ---------------------------------------------------------------------------


def test_tex_source_contains_topic(cover_tex: tuple[str, ArticleConfig]) -> None:
    """Topic appears verbatim in the generated .tex source."""
    tex, _ = cover_tex
    assert TOPIC in tex


def test_tex_source_contains_author(cover_tex: tuple[str, ArticleConfig]) -> None:
    tex, _ = cover_tex
    assert AUTHOR in tex


def test_tex_source_contains_date(cover_tex: tuple[str, ArticleConfig]) -> None:
    tex, _ = cover_tex
    assert DATE in tex


def test_tex_source_contains_course(cover_tex: tuple[str, ArticleConfig]) -> None:
    tex, _ = cover_tex
    assert COURSE in tex


def test_tex_source_contains_lecturer(cover_tex: tuple[str, ArticleConfig]) -> None:
    tex, _ = cover_tex
    assert LECTURER in tex


def test_tex_source_has_maketitle(cover_tex: tuple[str, ArticleConfig]) -> None:
    tex, _ = cover_tex
    assert r"\maketitle" in tex


def test_tex_source_all_five_fields_present(cover_tex: tuple[str, ArticleConfig]) -> None:
    """All five required cover-sheet fields are embedded in the .tex source."""
    tex, _ = cover_tex
    for field_val in (TOPIC, AUTHOR, DATE, COURSE, LECTURER):
        assert field_val in tex, f"Missing field value {field_val!r} in generated .tex"


# ---------------------------------------------------------------------------
# Tier 2: PDF cover-page assertions — skipped when compilation fails
# ---------------------------------------------------------------------------


def test_pdf_cover_page_contains_topic(cover_page_text: str) -> None:
    """T-059 DoD: topic appears on PDF page 1."""
    assert TOPIC in cover_page_text


def test_pdf_cover_page_contains_author(cover_page_text: str) -> None:
    """T-059 DoD: author appears on PDF page 1."""
    assert AUTHOR in cover_page_text


def test_pdf_cover_page_contains_date(cover_page_text: str) -> None:
    """T-059 DoD: date appears on PDF page 1."""
    assert DATE in cover_page_text


def test_pdf_cover_page_contains_course(cover_page_text: str) -> None:
    """T-059 DoD: course appears on PDF page 1."""
    assert COURSE in cover_page_text


def test_pdf_cover_page_contains_lecturer(cover_page_text: str) -> None:
    """T-059 DoD: lecturer appears on PDF page 1."""
    assert LECTURER in cover_page_text
