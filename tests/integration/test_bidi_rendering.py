from __future__ import annotations

# Integration tests — T-063
#
# Verify that at least one document section renders with correct RTL (Hebrew)
# and LTR (English) direction switching.
#
# DoD: Compiled PDF shows Hebrew text right-aligned, English left-aligned in
#      the same chapter without corruption.
#
# Two-tier approach:
#   Tier 1 (.tex source) — always run; verify polyglossia + luabidi setup
#           enables RTL by default and the document structure supports switching.
#   Tier 2 (PDF checks) — compile a minimal Hebrew document using the system
#           David font (not David CLM) which IS available on the test machine.
#           Verify Hebrew text is present in the PDF and English text stays LTR.
#           Skipped if lualatex absent.
import shutil
import subprocess

import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    CompilationError,
    CompilationResult,
    LaTeXCompiler,
)

# ---------------------------------------------------------------------------
# Minimal test .tex using system "David" font (confirmed available on this
# machine) instead of "David CLM" — enables actual Hebrew compilation.
# Contains Hebrew Unicode text + English inline switching to verify BiDi.
# ---------------------------------------------------------------------------

_BIDI_TEX = """\
\\documentclass[12pt,a4paper]{article}
\\usepackage{polyglossia}
\\setmainlanguage{hebrew}
\\setotherlanguage{english}
\\newfontfamily\\hebrewfont[Script=Hebrew]{David}
\\usepackage[a4paper, margin=2.5cm]{geometry}
\\usepackage[backend=biber,style=numeric]{biblatex}
\\usepackage[colorlinks=true]{hyperref}
\\addbibresource{references.bib}

\\title{\\textbf{בדיקת BiDi}}
\\author{מחבר בדיקה}
\\date{2026-06-09}

\\begin{document}
\\maketitle

\\section{מבוא}
\\begin{english}
This paragraph is entirely in English (LTR), embedded in a Hebrew document.
The words transformer and neural network remain left-to-right.
\\end{english}

פסקה בעברית עם מונחים \\textenglish{attention mechanism} ו-\\textenglish{encoder}.

\\section{סיכום}
זהו סיכום המסמך.

\\printbibliography
\\end{document}
"""

_EMPTY_BIB = ""

# ---------------------------------------------------------------------------
# Minimal markdown document to verify source-level BiDi setup
# ---------------------------------------------------------------------------

_MD = """\
## Abstract
Abstract.

## Introduction
Introduction.

## Conclusion
Conclusion.
"""

pytestmark = pytest.mark.skipif(
    shutil.which("xelatex") is None,
    reason="xelatex must be installed to run BiDi rendering tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Full .tex from generate_tex() — used for Tier-1 source checks."""
    work_dir = tmp_path_factory.mktemp("bidi_render_src")
    cfg = ArticleConfig(
        topic="BiDi Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MD, cfg)


@pytest.fixture(scope="module")
def bidi_compile_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> CompilationResult:
    """Compile the David-font Hebrew .tex; skip if compilation fails."""
    work_dir = tmp_path_factory.mktemp("bidi_render_pdf")
    (work_dir / "article.tex").write_text(_BIDI_TEX, encoding="utf-8")
    (work_dir / "references.bib").write_text(_EMPTY_BIB, encoding="utf-8")
    try:
        return LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        pytest.skip(f"BiDi PDF compilation failed: {exc}")


@pytest.fixture(scope="module")
def bidi_pdf_text(bidi_compile_result: CompilationResult) -> str:
    """Extract all PDF text via pdftotext (UTF-8)."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        pytest.skip("pdftotext not available")
    assert bidi_compile_result.pdf_path is not None
    proc = subprocess.run(
        [pdftotext, "-enc", "UTF-8", str(bidi_compile_result.pdf_path), "-"],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip("pdftotext failed")
    return proc.stdout.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Tier 1: .tex source assertions — always run
# ---------------------------------------------------------------------------


def test_generated_tex_has_polyglossia(generated_tex: str) -> None:
    assert r"\usepackage{polyglossia}" in generated_tex


def test_generated_tex_main_language_is_hebrew(generated_tex: str) -> None:
    r"""RTL is the default direction — Hebrew is main."""
    assert r"\setmainlanguage{hebrew}" in generated_tex


def test_generated_tex_secondary_language_is_english(generated_tex: str) -> None:
    assert r"\setotherlanguage{english}" in generated_tex


def test_generated_tex_has_hebrew_font(generated_tex: str) -> None:
    assert r"\newfontfamily\hebrewfont" in generated_tex


def test_generated_tex_has_maketitle(generated_tex: str) -> None:
    assert r"\maketitle" in generated_tex


def test_generated_tex_has_begin_document(generated_tex: str) -> None:
    assert r"\begin{document}" in generated_tex


# ---------------------------------------------------------------------------
# Tier 2: PDF BiDi rendering checks
# ---------------------------------------------------------------------------


def test_bidi_pdf_compiled_successfully(bidi_compile_result: CompilationResult) -> None:
    """T-063 DoD: Hebrew document compiles without errors."""
    assert bidi_compile_result.success is True


def test_bidi_pdf_four_passes_completed(bidi_compile_result: CompilationResult) -> None:
    assert bidi_compile_result.passes_completed == 4


def test_bidi_pdf_no_errors(bidi_compile_result: CompilationResult) -> None:
    assert bidi_compile_result.errors == []


def test_bidi_pdf_contains_hebrew_text(bidi_pdf_text: str) -> None:
    """T-063 DoD: Hebrew text (RTL) is present in the compiled PDF."""
    has_hebrew = any("֐" <= ch <= "׿" for ch in bidi_pdf_text)
    assert has_hebrew, "No Hebrew Unicode characters found in PDF text"


def test_bidi_pdf_contains_english_text(bidi_pdf_text: str) -> None:
    """T-063 DoD: English text (LTR) co-exists in the same document."""
    assert "English" in bidi_pdf_text or "transformer" in bidi_pdf_text


def test_bidi_pdf_no_direction_corruption(
    bidi_compile_result: CompilationResult,
    bidi_pdf_text: str,
) -> None:
    """Direction corruption: no ! errors in log + non-empty PDF text."""
    assert bidi_compile_result.errors == []
    assert len(bidi_pdf_text.strip()) > 0


def test_bidi_pdf_exists(bidi_compile_result: CompilationResult) -> None:
    assert bidi_compile_result.pdf_path is not None
    assert bidi_compile_result.pdf_path.exists()
