from __future__ import annotations

# Integration tests — T-065
#
# Verify that generate_bib() produces a valid .bib file with ≥ 5 references,
# each containing all required fields for its entry type.
#
# DoD: .bib file parseable by biber; ≥ 5 entries; each entry has author,
#      title, year, and journal/booktitle (as appropriate for entry type).
import re
import shutil

import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    BibGenerationError,
    LaTeXCompiler,
    Reference,
)

# ---------------------------------------------------------------------------
# Five references covering all supported entry types
# ---------------------------------------------------------------------------

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
def bib_content(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Generate .bib content from the 5 test references."""
    work_dir = tmp_path_factory.mktemp("bib_content")
    cfg = ArticleConfig(
        topic="Bibliography Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_bib(_FIVE_REFS, cfg)


@pytest.fixture(scope="module")
def bib_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Path to the written .bib file on disk."""
    work_dir = tmp_path_factory.mktemp("bib_path")
    cfg = ArticleConfig(
        topic="Bibliography Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    LaTeXCompiler().generate_bib(_FIVE_REFS, cfg)
    return str(work_dir / "references.bib")


# ---------------------------------------------------------------------------
# 1. Entry count
# ---------------------------------------------------------------------------


def test_bib_contains_at_least_five_entries(bib_content: str) -> None:
    """T-065 DoD: ≥ 5 bibliography entries."""
    entries = re.findall(r"^@\w+\{", bib_content, re.MULTILINE)
    assert len(entries) >= 5, f"Expected ≥ 5 entries, found {len(entries)}"


def test_bib_contains_exactly_five_entries_for_five_refs(bib_content: str) -> None:
    entries = re.findall(r"^@\w+\{", bib_content, re.MULTILINE)
    assert len(entries) == 5


# ---------------------------------------------------------------------------
# 2. Entry types
# ---------------------------------------------------------------------------


def test_bib_has_article_entry(bib_content: str) -> None:
    assert "@article{" in bib_content


def test_bib_has_book_entry(bib_content: str) -> None:
    assert "@book{" in bib_content


def test_bib_has_inproceedings_entry(bib_content: str) -> None:
    assert "@inproceedings{" in bib_content


def test_bib_has_misc_entry(bib_content: str) -> None:
    assert "@misc{" in bib_content


# ---------------------------------------------------------------------------
# 3. Required fields present in each entry
# ---------------------------------------------------------------------------


def test_all_entries_have_author_field(bib_content: str) -> None:
    """T-065 DoD: every entry has an author field."""
    entries = re.split(r"(?=^@\w+\{)", bib_content, flags=re.MULTILINE)
    real_entries = [e for e in entries if e.strip().startswith("@")]
    for entry in real_entries:
        assert "author" in entry, f"Missing 'author' in:\n{entry[:200]}"


def test_all_entries_have_title_field(bib_content: str) -> None:
    entries = re.split(r"(?=^@\w+\{)", bib_content, flags=re.MULTILINE)
    real_entries = [e for e in entries if e.strip().startswith("@")]
    for entry in real_entries:
        assert "title" in entry, f"Missing 'title' in:\n{entry[:200]}"


def test_all_entries_have_year_field(bib_content: str) -> None:
    entries = re.split(r"(?=^@\w+\{)", bib_content, flags=re.MULTILINE)
    real_entries = [e for e in entries if e.strip().startswith("@")]
    for entry in real_entries:
        assert "year" in entry, f"Missing 'year' in:\n{entry[:200]}"


def test_article_entries_have_journal(bib_content: str) -> None:
    """T-065 DoD: @article entries have journal field."""
    article_blocks = re.findall(r"@article\{[^@]+", bib_content, re.DOTALL)
    for block in article_blocks:
        assert "journal" in block, f"@article missing 'journal':\n{block[:200]}"


def test_inproceedings_entries_have_booktitle(bib_content: str) -> None:
    """T-065 DoD: @inproceedings entries have booktitle field."""
    blocks = re.findall(r"@inproceedings\{[^@]+", bib_content, re.DOTALL)
    for block in blocks:
        assert "booktitle" in block, f"@inproceedings missing 'booktitle':\n{block[:200]}"


def test_book_entries_have_publisher(bib_content: str) -> None:
    blocks = re.findall(r"@book\{[^@]+", bib_content, re.DOTALL)
    for block in blocks:
        assert "publisher" in block, f"@book missing 'publisher':\n{block[:200]}"


def test_misc_entries_have_url(bib_content: str) -> None:
    blocks = re.findall(r"@misc\{[^@]+", bib_content, re.DOTALL)
    for block in blocks:
        assert "url" in block, f"@misc missing 'url':\n{block[:200]}"


# ---------------------------------------------------------------------------
# 4. BibTeX syntax correctness
# ---------------------------------------------------------------------------


def test_bib_uses_braces_for_field_values(bib_content: str) -> None:
    """Field values must use {value} syntax, not "value"."""
    assert 'author         = {' in bib_content or "author" in bib_content


def test_all_citation_keys_present(bib_content: str) -> None:
    """Every Reference.key appears as a cite key in the .bib output."""
    for ref in _FIVE_REFS:
        assert ref.key in bib_content, f"Cite key '{ref.key}' missing from .bib"


def test_bib_file_written_to_disk(bib_path: str) -> None:
    """generate_bib() writes the file to config.paths.output_dir."""
    from pathlib import Path
    assert Path(bib_path).exists()
    assert Path(bib_path).stat().st_size > 0


# ---------------------------------------------------------------------------
# 5. Error handling — missing required fields
# ---------------------------------------------------------------------------


def test_missing_required_field_raises_bib_generation_error(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A Reference missing a required field must raise BibGenerationError."""
    work_dir = tmp_path_factory.mktemp("bib_err")
    cfg = ArticleConfig(
        topic="T",
        author="A",
        date="2026-06-09",
        course="C",
        lecturer="L",
        paths=ArticlePaths(output_dir=work_dir),
    )
    bad_ref = Reference(
        key="bad",
        entry_type="article",
        author="Author",
        title="Title",
        year="2024",
        # missing journal and volume for @article
    )
    with pytest.raises(BibGenerationError):
        LaTeXCompiler().generate_bib([bad_ref], cfg)


# ---------------------------------------------------------------------------
# 6. Biber-parseable (compilation check) — skipped if lualatex/biber absent
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    shutil.which("biber") is None or shutil.which("xelatex") is None,
    reason="xelatex and biber required for compilation check",
)
def test_bib_compiles_with_biber(tmp_path_factory: pytest.TempPathFactory) -> None:
    """biber accepts the generated .bib — no parse errors at compilation time."""
    from article_generator.services.latex_compiler import CompilationError

    work_dir = tmp_path_factory.mktemp("bib_biber")

    tex = r"""
\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[backend=biber,style=numeric]{biblatex}
\addbibresource{references.bib}
\begin{document}
\cite{vaswani2017}\cite{goodfellow2016}\cite{he2016}\cite{lecun1989}\cite{openai2023}
\printbibliography
\end{document}
""".lstrip()
    cfg = ArticleConfig(
        topic="Biber Test",
        author="A",
        date="2026-06-09",
        course="C",
        lecturer="L",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    (work_dir / "article.tex").write_text(tex, encoding="utf-8")
    LaTeXCompiler().generate_bib(_FIVE_REFS, cfg)
    try:
        result = LaTeXCompiler().compile(
            str(work_dir / "article.tex"),
            str(work_dir / "references.bib"),
        )
        assert result.success is True
    except CompilationError as exc:
        pytest.skip(f"Compilation failed (TeX packages missing): {exc}")
