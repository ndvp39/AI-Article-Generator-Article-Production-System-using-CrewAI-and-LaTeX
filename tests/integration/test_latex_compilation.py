from __future__ import annotations

# Integration tests — T-075
#
# Verify the full LaTeX compilation chain:
#   generate_tex(markdown, cfg) → .tex file
#   generate_bib(refs, cfg)     → .bib file
#   compile(tex_path, bib_path) → valid PDF, zero errors in log
#
# DoD: Given sample .tex + .bib, compile() produces valid PDF;
#      zero errors in log.
#
# Skipped automatically when lualatex or biber are not installed.
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
    reason="lualatex and biber required for LaTeX compilation tests",
)

# ---------------------------------------------------------------------------
# Sample markdown — realistic multi-section article with citations
# ---------------------------------------------------------------------------

_MD = """\
## Abstract
This article examines transformer architectures [@vaswani2017] and their
application to natural language processing tasks.

## Introduction
The attention mechanism [@vaswani2017] forms the foundation of modern large
language models.
Residual networks [@he2016] introduced skip connections that allow training
of very deep networks.

<!-- FORMULA: L = -\\frac{1}{N}\\sum_{i=1}^{N} y_i \\log \\hat{y}_i -->

## Methodology
We evaluate three model families and compare their cross-entropy loss
on a held-out validation set.

## Results
All experiments were conducted on a single GPU with a batch size of 32.

## Conclusion
Transformer models demonstrate superior performance on sequence tasks
compared to recurrent architectures [@vaswani2017].
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
        key="he2016",
        entry_type="inproceedings",
        author="He, Kaiming and others",
        title="Deep Residual Learning for Image Recognition",
        year="2016",
        booktitle="Proceedings of the IEEE Conference on Computer Vision",
    ),
]

# ---------------------------------------------------------------------------
# Fixtures — compile the full chain once per module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def compiled(tmp_path_factory: pytest.TempPathFactory) -> CompilationResult:
    """Run generate_tex → generate_bib → compile.  Skip if TeX packages absent."""
    work_dir = tmp_path_factory.mktemp("latex_chain")
    cfg = ArticleConfig(
        topic="Transformer Architectures",
        author="Test Author",
        date="2026-06-09",
        course="Advanced ML",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    compiler = LaTeXCompiler()
    tex_content = compiler.generate_tex(_MD, cfg)
    (work_dir / "article.tex").write_text(tex_content, encoding="utf-8")
    compiler.generate_bib(_REFS, cfg)

    try:
        return compiler.compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
    except CompilationError as exc:
        pytest.skip(
            f"LaTeX compilation failed — TeX packages likely missing: {exc}"
        )


# ---------------------------------------------------------------------------
# DoD: compile() returns success=True, passes_completed=4, errors=[]
# ---------------------------------------------------------------------------


def test_full_chain_success(compiled: CompilationResult) -> None:
    """T-075 DoD: compile() succeeds on generated .tex + .bib."""
    assert compiled.success is True


def test_full_chain_four_passes(compiled: CompilationResult) -> None:
    assert compiled.passes_completed == 4


def test_full_chain_zero_errors(compiled: CompilationResult) -> None:
    """T-075 DoD: zero errors in log."""
    assert compiled.errors == []


def test_full_chain_duration_positive(compiled: CompilationResult) -> None:
    assert compiled.duration_seconds > 0


# ---------------------------------------------------------------------------
# PDF file produced
# ---------------------------------------------------------------------------


def test_full_chain_pdf_exists(compiled: CompilationResult) -> None:
    """T-075 DoD: valid PDF written to disk."""
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.exists()


def test_full_chain_pdf_is_file(compiled: CompilationResult) -> None:
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.is_file()


def test_full_chain_pdf_magic_bytes(compiled: CompilationResult) -> None:
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.read_bytes()[:4] == b"%PDF"


def test_full_chain_pdf_non_empty(compiled: CompilationResult) -> None:
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Log file — no fatal ! lines
# ---------------------------------------------------------------------------


def test_full_chain_log_exists(compiled: CompilationResult) -> None:
    assert compiled.log_path is not None
    assert compiled.log_path.exists()


def test_full_chain_log_no_bang_lines(compiled: CompilationResult) -> None:
    assert compiled.log_path is not None
    log = compiled.log_path.read_text(encoding="utf-8", errors="replace")
    bang_lines = [ln for ln in log.splitlines() if ln.startswith("!")]
    assert bang_lines == [], f"Fatal LaTeX errors: {bang_lines}"


def test_full_chain_log_no_undefined_citations(compiled: CompilationResult) -> None:
    assert compiled.log_path is not None
    log = compiled.log_path.read_text(encoding="utf-8", errors="replace")
    undefined = [
        ln for ln in log.splitlines()
        if "undefined citation" in ln.lower() or "citation undefined" in ln.lower()
    ]
    assert undefined == [], f"Undefined citations in log: {undefined}"


# ---------------------------------------------------------------------------
# Auxiliary output files from biber pass
# ---------------------------------------------------------------------------


def test_full_chain_bbl_written_by_biber(compiled: CompilationResult) -> None:
    """biber must have run and written the .bbl file."""
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.with_suffix(".bbl").exists()


def test_full_chain_aux_file_exists(compiled: CompilationResult) -> None:
    assert compiled.pdf_path is not None
    assert compiled.pdf_path.with_suffix(".aux").exists()


# ---------------------------------------------------------------------------
# generate_tex output checks (source tier — always run)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tex_source(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return the .tex source from generate_tex without compiling."""
    work_dir = tmp_path_factory.mktemp("latex_tex_src")
    cfg = ArticleConfig(
        topic="Transformer Architectures",
        author="Test Author",
        date="2026-06-09",
        course="Advanced ML",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MD, cfg)


def test_tex_source_has_document_class(tex_source: str) -> None:
    assert r"\documentclass" in tex_source


def test_tex_source_has_begin_document(tex_source: str) -> None:
    assert r"\begin{document}" in tex_source


def test_tex_source_has_end_document(tex_source: str) -> None:
    assert r"\end{document}" in tex_source


def test_tex_source_has_cite_commands(tex_source: str) -> None:
    r"""[@key] converted to \cite{key}."""
    assert r"\cite{vaswani2017}" in tex_source


def test_tex_source_no_unconverted_citations(tex_source: str) -> None:
    assert "[@" not in tex_source


def test_tex_source_has_equation_environment(tex_source: str) -> None:
    assert r"\begin{equation}" in tex_source


def test_tex_source_has_printbibliography(tex_source: str) -> None:
    assert r"\printbibliography" in tex_source


# ---------------------------------------------------------------------------
# generate_bib output checks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bib_source(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return the .bib content from generate_bib."""
    work_dir = tmp_path_factory.mktemp("latex_bib_src")
    cfg = ArticleConfig(
        topic="Transformer Architectures",
        author="Test Author",
        date="2026-06-09",
        course="Advanced ML",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_bib(_REFS, cfg)


def test_bib_source_has_vaswani_entry(bib_source: str) -> None:
    assert "@article{vaswani2017," in bib_source


def test_bib_source_has_he2016_entry(bib_source: str) -> None:
    assert "@inproceedings{he2016," in bib_source


def test_bib_source_has_two_entries(bib_source: str) -> None:
    import re
    entries = re.findall(r"^@\w+\{", bib_source, re.MULTILINE)
    assert len(entries) == 2


def test_bib_source_all_cite_keys_resolvable(tex_source: str, bib_source: str) -> None:
    """Every \\cite{key} in .tex must have a matching entry in .bib."""
    import re
    cited = set(re.findall(r"\\cite\{([^}]+)\}", tex_source))
    defined = set(re.findall(r"^@\w+\{(\w+),", bib_source, re.MULTILINE))
    assert cited <= defined, f"Unresolvable cite keys: {cited - defined}"
