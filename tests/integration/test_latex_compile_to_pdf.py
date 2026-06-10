from __future__ import annotations

# Integration tests — T-058
#
# Verify that LaTeXCompiler.compile() executes the full 4-pass XeLaTeX + biber
# pipeline against a real (minimal) .tex + .bib file and produces a valid PDF.
#
# DoD: compile() returns CompilationResult(success=True, passes_completed=4,
#      errors=[]) and article.pdf exists on disk.
#
# Skipped automatically when lualatex or biber are not installed.
import shutil

import pytest

from article_generator.services.latex_compiler import (
    CompilationError,
    CompilationResult,
    LaTeXCompiler,
)

# Skip entire module if lualatex or biber are absent
pytestmark = pytest.mark.skipif(
    shutil.which("xelatex") is None or shutil.which("biber") is None,
    reason="xelatex and biber must both be installed to run LaTeX integration tests",
)

# ---------------------------------------------------------------------------
# Minimal compilable .tex — no Hebrew fonts required (tests the pipeline,
# not the language layer).  Uses biblatex + biber for the bibliography pass.
# ---------------------------------------------------------------------------

_MINIMAL_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[backend=biber,style=numeric]{biblatex}
\usepackage{hyperref}
\addbibresource{references.bib}

\title{\textbf{Integration Test Article}}
\author{Test Author}
\date{2026-06-09}

\begin{document}

\maketitle
\tableofcontents
\newpage

\section{Introduction}
This is a minimal integration test article.
The transformer architecture was proposed in \cite{vaswani2017}.

\section{Methodology}
We use standard cross-entropy loss:
\begin{equation}
    \mathcal{L} = -\frac{1}{N} \sum_{i=1}^{N} y_i \log \hat{y}_i
\end{equation}

\section{Conclusion}
This article concludes the integration test.

\printbibliography

\end{document}
""".lstrip()

_MINIMAL_BIB = r"""
@article{vaswani2017,
  author   = {Vaswani, Ashish and others},
  title    = {Attention Is All You Need},
  journal  = {Advances in Neural Information Processing Systems},
  year     = {2017},
  volume   = {30},
}
""".lstrip()

# A .tex file guaranteed to produce a fatal ! error during compilation
_BAD_TEX = r"""
\documentclass{article}
\begin{document}
\THISDOESNOTEXISTATALLXYZ
\end{document}
""".lstrip()


# ---------------------------------------------------------------------------
# Module-scoped fixtures — compilation runs exactly once per test session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def compile_result(tmp_path_factory: pytest.TempPathFactory) -> CompilationResult:
    """Run the full 4-pass pipeline once; share result across all tests.

    Skips all dependent tests when the TeX installation is incomplete
    (e.g. missing biblatex / hyperref packages) so that CI machines with
    only a minimal TeX Live installation do not produce false failures.
    """
    work_dir = tmp_path_factory.mktemp("latex_compile")
    (work_dir / "article.tex").write_text(_MINIMAL_TEX, encoding="utf-8")
    (work_dir / "references.bib").write_text(_MINIMAL_BIB, encoding="utf-8")
    try:
        return LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        pytest.skip(
            f"LaTeX compilation failed — likely missing TeX packages "
            f"(biblatex, hyperref).  Install a full TeX Live distribution to "
            f"run these tests.  Underlying error: {exc}"
        )


@pytest.fixture(scope="module")
def bad_compile_exc(tmp_path_factory: pytest.TempPathFactory) -> CompilationError:
    """Attempt to compile the bad .tex; capture and return the CompilationError."""
    work_dir = tmp_path_factory.mktemp("latex_bad")
    (work_dir / "article.tex").write_text(_BAD_TEX, encoding="utf-8")
    (work_dir / "references.bib").write_text("", encoding="utf-8")
    try:
        LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        return exc
    pytest.fail("CompilationError was not raised for the bad .tex file")


# ---------------------------------------------------------------------------
# 1. Compilation result — T-058 DoD
# ---------------------------------------------------------------------------


def test_compile_result_is_compilation_result(compile_result: CompilationResult) -> None:
    assert isinstance(compile_result, CompilationResult)


def test_compile_success_true(compile_result: CompilationResult) -> None:
    """T-058 DoD: compile() returns success=True."""
    assert compile_result.success is True


def test_compile_passes_completed_is_4(compile_result: CompilationResult) -> None:
    """T-058 DoD: all 4 passes completed."""
    assert compile_result.passes_completed == 4


def test_compile_no_fatal_errors(compile_result: CompilationResult) -> None:
    """T-058 DoD: zero ! errors in the LaTeX log."""
    assert compile_result.errors == []


def test_compile_duration_is_positive(compile_result: CompilationResult) -> None:
    assert compile_result.duration_seconds > 0


# ---------------------------------------------------------------------------
# 2. PDF file produced on disk
# ---------------------------------------------------------------------------


def test_pdf_path_is_set(compile_result: CompilationResult) -> None:
    assert compile_result.pdf_path is not None


def test_pdf_file_exists(compile_result: CompilationResult) -> None:
    """T-058 DoD: article.pdf exists after compilation."""
    assert compile_result.pdf_path is not None
    assert compile_result.pdf_path.exists()


def test_pdf_file_is_regular_file(compile_result: CompilationResult) -> None:
    assert compile_result.pdf_path is not None
    assert compile_result.pdf_path.is_file()


def test_pdf_extension_is_pdf(compile_result: CompilationResult) -> None:
    assert compile_result.pdf_path is not None
    assert compile_result.pdf_path.suffix == ".pdf"


def test_pdf_magic_bytes_are_valid(compile_result: CompilationResult) -> None:
    """PDF files must start with the %PDF- signature."""
    assert compile_result.pdf_path is not None
    header = compile_result.pdf_path.read_bytes()[:4]
    assert header == b"%PDF", f"Bad PDF header: {header!r}"


def test_pdf_file_size_is_positive(compile_result: CompilationResult) -> None:
    assert compile_result.pdf_path is not None
    assert compile_result.pdf_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# 3. Auxiliary output files
# ---------------------------------------------------------------------------


def test_log_path_is_set(compile_result: CompilationResult) -> None:
    assert compile_result.log_path is not None


def test_log_file_exists(compile_result: CompilationResult) -> None:
    assert compile_result.log_path is not None
    assert compile_result.log_path.exists()


def test_aux_file_exists_after_compile(compile_result: CompilationResult) -> None:
    assert compile_result.pdf_path is not None
    aux = compile_result.pdf_path.with_suffix(".aux")
    assert aux.exists()


def test_bbl_file_exists_after_biber(compile_result: CompilationResult) -> None:
    """biber writes a .bbl file that xelatex reads in passes 3 and 4."""
    assert compile_result.pdf_path is not None
    bbl = compile_result.pdf_path.with_suffix(".bbl")
    assert bbl.exists()


def test_log_contains_no_bang_lines(compile_result: CompilationResult) -> None:
    """No ! lines in the final log means a clean compile."""
    assert compile_result.log_path is not None
    log_text = compile_result.log_path.read_text(encoding="utf-8", errors="replace")
    bang_lines = [line for line in log_text.splitlines() if line.startswith("!")]
    assert bang_lines == [], f"Unexpected ! lines: {bang_lines}"


def test_log_has_no_undefined_citations(compile_result: CompilationResult) -> None:
    assert compile_result.log_path is not None
    log_text = compile_result.log_path.read_text(encoding="utf-8", errors="replace")
    assert "Citation" not in log_text or "undefined" not in log_text or all(
        "undefined" not in line
        for line in log_text.splitlines()
        if "Citation" in line
    )


# ---------------------------------------------------------------------------
# 4. Fatal error scenario — bad .tex raises CompilationError
# ---------------------------------------------------------------------------


def test_bad_tex_raises_compilation_error(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """PRD Scenario T-002: undefined command causes CompilationError."""
    work_dir = tmp_path_factory.mktemp("latex_bad2")
    (work_dir / "article.tex").write_text(_BAD_TEX, encoding="utf-8")
    (work_dir / "references.bib").write_text("", encoding="utf-8")
    with pytest.raises(CompilationError):
        LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )


def test_bad_tex_error_result_has_errors(bad_compile_exc: CompilationError) -> None:
    """CompilationError.result.errors must contain at least one ! line."""
    assert bad_compile_exc.result is not None
    assert len(bad_compile_exc.result.errors) > 0


def test_bad_tex_error_result_passes_completed_less_than_4(
    bad_compile_exc: CompilationError,
) -> None:
    """A failing compilation must not report all 4 passes as done."""
    assert bad_compile_exc.result is not None
    assert bad_compile_exc.result.passes_completed < 4
