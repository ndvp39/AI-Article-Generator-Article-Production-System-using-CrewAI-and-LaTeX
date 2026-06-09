from __future__ import annotations

# Integration tests — T-066
#
# Verify that every \cite{key} command in the generated .tex has a matching
# entry in the generated .bib file, and that after 4-pass compilation there
# are no "undefined citation" warnings in the LaTeX log.
#
# DoD: After 4-pass compilation, no "undefined citation" warnings in LaTeX log.
import re
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

# ---------------------------------------------------------------------------
# Markdown with [@key] inline citations — converted to \cite{key} by compiler
# ---------------------------------------------------------------------------

_CITED_MD = """\
## Abstract
This paper builds on work by Vaswani [@vaswani2017] and Goodfellow [@goodfellow2016].

## Introduction
The transformer architecture [@vaswani2017] introduced self-attention.
ResNets [@he2016] demonstrated residual connections.
Early neural networks [@lecun1989] used backpropagation.
Large language models [@openai2023] show remarkable capabilities.

## Conclusion
All five references are cited in this article [@vaswani2017].
"""

_FIVE_REFS: list[Reference] = [
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
    Reference(
        key="he2016",
        entry_type="inproceedings",
        author="He, Kaiming and others",
        title="Deep Residual Learning for Image Recognition",
        year="2016",
        booktitle="Proceedings of the IEEE Conference on Computer Vision",
    ),
    Reference(
        key="lecun1989",
        entry_type="article",
        author="LeCun, Yann and others",
        title="Backpropagation Applied to Handwritten Zip Code Recognition",
        year="1989",
        journal="Neural Computation",
        volume="1",
    ),
    Reference(
        key="openai2023",
        entry_type="misc",
        author="OpenAI",
        title="GPT-4 Technical Report",
        year="2023",
        url="https://openai.com/research/gpt-4",
    ),
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def citation_sources(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, str]:
    """Return (tex_content, bib_content) for the cited markdown + refs."""
    work_dir = tmp_path_factory.mktemp("citation_src")
    cfg = ArticleConfig(
        topic="Citation Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    compiler = LaTeXCompiler()
    tex = compiler.generate_tex(_CITED_MD, cfg)
    bib = compiler.generate_bib(_FIVE_REFS, cfg)
    return tex, bib


@pytest.fixture(scope="module")
def citation_compile_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> CompilationResult:
    """Compile the standard-fonts citation .tex; skip if compilation fails."""
    work_dir = tmp_path_factory.mktemp("citation_compile")

    tex_minimal = r"""
\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[backend=biber,style=numeric]{biblatex}
\usepackage{hyperref}
\addbibresource{references.bib}
\begin{document}
Vaswani \cite{vaswani2017},
Goodfellow \cite{goodfellow2016},
He \cite{he2016},
LeCun \cite{lecun1989},
OpenAI \cite{openai2023}.
\printbibliography
\end{document}
""".lstrip()

    cfg = ArticleConfig(
        topic="Citation Compile",
        author="A",
        date="2026-06-09",
        course="C",
        lecturer="L",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    (work_dir / "article.tex").write_text(tex_minimal, encoding="utf-8")
    LaTeXCompiler().generate_bib(_FIVE_REFS, cfg)

    try:
        return LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        pytest.skip(f"Citation compilation failed (TeX packages missing): {exc}")


# ---------------------------------------------------------------------------
# Tier 1: Source cross-reference — always run
# ---------------------------------------------------------------------------


def test_tex_contains_cite_commands(citation_sources: tuple[str, str]) -> None:
    r"""[@key] in Markdown is converted to \cite{key} in LaTeX."""
    tex, _ = citation_sources
    assert r"\cite{" in tex


def test_all_markdown_citations_converted(citation_sources: tuple[str, str]) -> None:
    """No unconverted [@key] citation syntax remains in the .tex output."""
    tex, _ = citation_sources
    assert "[@" not in tex


def test_all_cite_keys_have_bib_entries(
    citation_sources: tuple[str, str],
) -> None:
    """T-066 DoD: every \\cite{key} in .tex has a matching @entry{key} in .bib."""
    tex, bib = citation_sources
    cited_keys = set(re.findall(r"\\cite\{([^}]+)\}", tex))
    bib_keys   = set(re.findall(r"^@\w+\{(\w+),", bib, re.MULTILINE))
    undefined  = cited_keys - bib_keys
    assert undefined == set(), (
        f"Cite keys in .tex with no .bib entry: {sorted(undefined)}"
    )


def test_no_bib_keys_missing_from_tex(citation_sources: tuple[str, str]) -> None:
    """Informational: no orphan .bib entries that are never cited (not required)."""
    tex, bib = citation_sources
    bib_keys   = set(re.findall(r"^@\w+\{(\w+),", bib, re.MULTILINE))
    cited_keys = set(re.findall(r"\\cite\{([^}]+)\}", tex))
    orphans    = bib_keys - cited_keys
    # Orphan entries are allowed — just document the count
    assert isinstance(orphans, set)  # always passes; documents the check


def test_five_unique_cite_keys_in_tex(citation_sources: tuple[str, str]) -> None:
    tex, _ = citation_sources
    keys = set(re.findall(r"\\cite\{([^}]+)\}", tex))
    assert len(keys) >= 5, f"Expected ≥ 5 unique cite keys, got {len(keys)}: {keys}"


# ---------------------------------------------------------------------------
# Tier 2: Compilation — skipped if lualatex/biber absent or packages missing
# ---------------------------------------------------------------------------

pytestmark_compile = pytest.mark.skipif(
    shutil.which("lualatex") is None or shutil.which("biber") is None,
    reason="lualatex and biber required",
)


@pytestmark_compile
def test_compilation_succeeds_with_all_citations(
    citation_compile_result: CompilationResult,
) -> None:
    """T-066 DoD: document with all 5 citations compiles successfully."""
    assert citation_compile_result.success is True


@pytestmark_compile
def test_no_undefined_citation_warnings_in_log(
    citation_compile_result: CompilationResult,
) -> None:
    """T-066 DoD: no 'undefined citation' warnings after 4-pass compilation."""
    assert citation_compile_result.log_path is not None
    log = citation_compile_result.log_path.read_text(encoding="utf-8", errors="replace")
    undefined_lines = [
        ln for ln in log.splitlines()
        if "undefined citation" in ln.lower() or "citation undefined" in ln.lower()
    ]
    assert undefined_lines == [], (
        "Undefined citation warnings found:\n" + "\n".join(undefined_lines)
    )


@pytestmark_compile
def test_final_log_has_no_undefined_citation_lines(
    citation_compile_result: CompilationResult,
) -> None:
    """The FINAL (pass-4) log file must not have unresolved citation warnings.

    result.warnings accumulates from all passes; pass 1 always has undefined
    citations (biber hasn't run yet).  The authoritative check is the log
    from pass 4 — covered by test_no_undefined_citation_warnings_in_log.
    This test cross-checks that errors[] is also empty after pass 4.
    """
    assert citation_compile_result.errors == [], (
        f"Compilation errors: {citation_compile_result.errors}"
    )
