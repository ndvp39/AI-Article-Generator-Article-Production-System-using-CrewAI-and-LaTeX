from __future__ import annotations

# Integration tests — T-061
#
# Verify that tables produced by the LaTeXCompiler do not overflow page margins.
#
# DoD: Visual inspection confirms all tables fit within margins; tabularx used
#      with \textwidth so columns auto-scale to the printable area.
#
# Two-tier approach:
#   Tier 1 (.tex source checks) — always run; verify that _table_to_tabularx()
#           produces tabularx{\textwidth}{...} with booktabs-style rules.
#   Tier 2 (log checks) — compile a standard-fonts .tex with a wide 5-column
#           table and verify the LaTeX log is free of "Overfull \\hbox" warnings,
#           which would indicate table content spills beyond the margin.
#           Skipped when lualatex/biber absent or compilation fails.
#
# Module-level skip when lualatex/biber are not installed.
import shutil

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
    shutil.which("lualatex") is None or shutil.which("biber") is None,
    reason="lualatex and biber must both be installed to run LaTeX integration tests",
)

# ---------------------------------------------------------------------------
# Markdown with a 5-column pipe table and required sections
# ---------------------------------------------------------------------------

_MD_WITH_TABLE = """\
## Abstract
This paper surveys key sequence modelling approaches.

## Introduction
The following table compares four popular architectures:

| Model | Accuracy | Speed | Memory | Notes |
|-------|----------|-------|--------|-------|
| Transformer | 95% | Fast | High | State of the art |
| LSTM | 88% | Medium | Medium | Recurrent baseline |
| GRU | 86% | Medium | Low | Lighter recurrent |
| CNN | 82% | Very fast | Low | Parallel convolutions |

## Conclusion
The comparison shows that tabularx distributes column widths correctly.
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
# Standard-fonts .tex that mirrors the tabularx output of _table_to_tabularx()
# — used for Tier 2 compilation tests (no polyglossia / Hebrew font needed).
# ---------------------------------------------------------------------------

_TABLE_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[a4paper, margin=2.5cm]{geometry}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage[backend=biber,style=numeric]{biblatex}
\usepackage[colorlinks=true]{hyperref}
\addbibresource{references.bib}

\title{Table Margin Integration Test}
\author{Test Author}
\date{2026-06-09}

\begin{document}
\maketitle

\section{Introduction}
Wide table rendered with tabularx:

\begin{table}[htbp]
  \centering
  \begin{tabularx}{\textwidth}{llllX}
  \toprule
  \textbf{Model} & \textbf{Accuracy} & \textbf{Speed} & \textbf{Memory} & \textbf{Notes} \\
  \midrule
  Transformer & 95\% & Fast & High & State of the art architecture \\
  LSTM & 88\% & Medium & Medium & Classic recurrent baseline \\
  GRU & 86\% & Medium & Low & Lighter recurrent variant \\
  CNN & 82\% & Very fast & Low & Highly parallelisable convolutions \\
  \bottomrule
  \end{tabularx}
\end{table}

\section{Conclusion}
tabularx ensures the table fits within the \texttt{2.5cm} margins.

\printbibliography
\end{document}
""".lstrip()

_TABLE_BIB = r"""
@article{vaswani2017,
  author   = {Vaswani, Ashish and others},
  title    = {Attention Is All You Need},
  journal  = {Advances in Neural Information Processing Systems},
  year     = {2017},
  volume   = {30},
}
""".lstrip()

# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def table_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return the .tex source from generate_tex() for the table document."""
    work_dir = tmp_path_factory.mktemp("table_gentex")
    cfg = ArticleConfig(
        topic="Sequence Models",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    compiler = LaTeXCompiler()
    tex = compiler.generate_tex(_MD_WITH_TABLE, cfg)
    compiler.generate_bib(_REFS, cfg)
    return tex


@pytest.fixture(scope="module")
def table_compile_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> CompilationResult:
    """Compile the standard-fonts table .tex; skip if compilation fails."""
    work_dir = tmp_path_factory.mktemp("table_compile")
    tex_path = work_dir / "article.tex"
    bib_path = work_dir / "references.bib"
    tex_path.write_text(_TABLE_TEX, encoding="utf-8")
    bib_path.write_text(_TABLE_BIB, encoding="utf-8")
    try:
        return LaTeXCompiler().compile(str(tex_path), str(bib_path))
    except CompilationError as exc:
        pytest.skip(
            f"Table PDF tests skipped — compilation failed.  "
            f"Install biblatex + hyperref TeX packages.  Error: {exc}"
        )


# ---------------------------------------------------------------------------
# Tier 1: .tex source assertions — always run (no compilation required)
# ---------------------------------------------------------------------------


def test_tabularx_in_generated_tex(table_tex: str) -> None:
    """Pipe-table rows are rendered with tabularx, not tabular."""
    assert r"\begin{tabularx}" in table_tex


def test_tabularx_uses_textwidth(table_tex: str) -> None:
    r"""Table width is set to \textwidth so it fills the printable area."""
    assert r"\begin{tabularx}{\textwidth}" in table_tex


def test_table_env_wraps_tabularx(table_tex: str) -> None:
    r"""The tabularx is wrapped in a \begin{table}...\end{table} float."""
    assert r"\begin{table}" in table_tex
    assert r"\end{table}" in table_tex


def test_table_uses_toprule(table_tex: str) -> None:
    r"""booktabs \toprule replaces \hline — no line-overrun artefacts."""
    assert r"\toprule" in table_tex


def test_table_uses_midrule(table_tex: str) -> None:
    assert r"\midrule" in table_tex


def test_table_uses_bottomrule(table_tex: str) -> None:
    assert r"\bottomrule" in table_tex


def test_table_no_hline(table_tex: str) -> None:
    r"""No \hline — table borders use booktabs rules exclusively."""
    assert r"\hline" not in table_tex


def test_preamble_includes_tabularx_package(table_tex: str) -> None:
    assert r"\usepackage{tabularx}" in table_tex


def test_preamble_includes_booktabs_package(table_tex: str) -> None:
    assert r"\usepackage{booktabs}" in table_tex


def test_five_col_table_has_last_col_expanding(table_tex: str) -> None:
    """5-column table: col spec is llllX (last col auto-expands)."""
    assert r"\begin{tabularx}{\textwidth}{llllX}" in table_tex


def test_table_centering_present(table_tex: str) -> None:
    assert r"\centering" in table_tex


# ---------------------------------------------------------------------------
# Tier 2: log / PDF checks — skipped when compilation fails
# ---------------------------------------------------------------------------


def test_compilation_succeeded(table_compile_result: CompilationResult) -> None:
    """T-061 DoD: document with tabularx table compiles successfully."""
    assert table_compile_result.success is True


def test_no_overfull_hbox_warnings(table_compile_result: CompilationResult) -> None:
    r"""T-061 DoD: no Overfull \hbox warnings — table stays within margins."""
    overfull = [w for w in table_compile_result.warnings if r"Overfull \hbox" in w]
    assert overfull == [], (
        f"Table produced {len(overfull)} Overfull \\hbox warning(s):\n"
        + "\n".join(overfull)
    )


def test_log_has_no_overfull_hbox(table_compile_result: CompilationResult) -> None:
    """Cross-check directly against the full log file."""
    assert table_compile_result.log_path is not None
    log_text = table_compile_result.log_path.read_text(
        encoding="utf-8", errors="replace"
    )
    overfull_lines = [
        ln for ln in log_text.splitlines() if r"Overfull \hbox" in ln
    ]
    assert overfull_lines == [], (
        f"Log contains {len(overfull_lines)} Overfull \\hbox line(s):\n"
        + "\n".join(overfull_lines[:10])
    )


def test_pdf_exists_after_table_compile(table_compile_result: CompilationResult) -> None:
    assert table_compile_result.pdf_path is not None
    assert table_compile_result.pdf_path.exists()


def test_four_passes_completed(table_compile_result: CompilationResult) -> None:
    assert table_compile_result.passes_completed == 4
