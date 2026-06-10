from __future__ import annotations

# T-057 — Unit tests for LaTeXCompiler
#
# Covers: generate_tex() preamble & body conversion (T-054),
#         generate_bib() entry formatting & validation (T-055),
#         compile() 4-pass pipeline & error handling (T-056).
#
# All subprocess.run calls are mocked so no LaTeX installation is needed.
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from article_generator.constants import BIBER_EXECUTABLE, LATEX_ENGINE
from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    BibGenerationError,
    CompilationError,
    CompilationResult,
    CompilationTimeoutError,
    LaTeXCompiler,
    LaTeXGenerationError,
    Reference,
)

# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

_MINIMAL_MD = r"""# Abstract
This is the abstract section.

# Introduction
This section introduces the work.

# Conclusion
This section concludes the work.
"""

_FULL_MD = r"""# Abstract
We study attention mechanisms.

# Introduction
The transformer [@vaswani2017] revolutionised NLP.

## Background
Previous work used **recurrent** networks and *convolutions*.

### Details
Inline `code` example here.

<!-- FORMULA: \nabla_\theta \mathcal{L} = \frac{1}{N}\sum_{i=1}^{N} \hat{y}_i -->

| Model | Accuracy | Parameters |
|-------|----------|------------|
| CNN | 0.85 | 1.2M |
| Transformer | 0.92 | 86M |

![Training loss](assets/graph.png)

See [OpenAI](https://openai.com) for details.

# Conclusion
We conclude that attention is all you need.
"""

_ARTICLE_REF = Reference(
    key="vaswani2017",
    entry_type="article",
    author="Vaswani, Ashish and others",
    title="Attention Is All You Need",
    journal="Advances in Neural Information Processing Systems",
    year="2017",
    volume="30",
)
_BOOK_REF = Reference(
    key="bishop2006",
    entry_type="book",
    author="Bishop, Christopher M.",
    title="Pattern Recognition and Machine Learning",
    publisher="Springer",
    year="2006",
)
_INPROC_REF = Reference(
    key="devlin2019",
    entry_type="inproceedings",
    author="Devlin, Jacob and others",
    title="BERT: Pre-training of Deep Bidirectional Transformers",
    booktitle="NAACL-HLT",
    year="2019",
)
_MISC_REF = Reference(
    key="openai2023",
    entry_type="misc",
    author="OpenAI",
    title="GPT-4 Technical Report",
    year="2023",
    url="https://openai.com/research/gpt-4",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def compiler() -> LaTeXCompiler:
    return LaTeXCompiler()


@pytest.fixture()
def cfg(tmp_path: Path) -> ArticleConfig:
    return ArticleConfig(
        topic="Machine Learning Study",
        author="Jane Doe",
        date="2026-06-09",
        course="AI Agents MSC",
        lecturer="Dr. Yoram Segal",
        paths=ArticlePaths(output_dir=tmp_path),
    )


@pytest.fixture()
def minimal_tex(compiler: LaTeXCompiler, cfg: ArticleConfig) -> str:
    return compiler.generate_tex(_MINIMAL_MD, cfg)


@pytest.fixture()
def full_tex(compiler: LaTeXCompiler, cfg: ArticleConfig) -> str:
    return compiler.generate_tex(_FULL_MD, cfg)


@pytest.fixture()
def tex_file(tmp_path: Path) -> Path:
    tex = tmp_path / "article.tex"
    tex.write_text(
        r"\documentclass{article}\begin{document}Hi\end{document}", encoding="utf-8"
    )
    return tex


@pytest.fixture()
def clean_log(tmp_path: Path) -> Path:
    log = tmp_path / "article.log"
    log.write_text("No errors here.\nNormal compilation.", encoding="utf-8")
    return log


@pytest.fixture()
def pdf_file(tmp_path: Path) -> Path:
    pdf = tmp_path / "article.pdf"
    pdf.write_bytes(b"%PDF-1.5")
    return pdf


@pytest.fixture()
def mock_ok() -> MagicMock:
    return MagicMock(returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# 1. generate_tex — preamble structure
# ---------------------------------------------------------------------------


def test_preamble_contains_polyglossia(minimal_tex: str) -> None:
    assert r"\usepackage{polyglossia}" in minimal_tex


def test_preamble_sets_main_language_hebrew(minimal_tex: str) -> None:
    assert r"\setmainlanguage{hebrew}" in minimal_tex


def test_preamble_sets_other_language_english(minimal_tex: str) -> None:
    assert r"\setotherlanguage{english}" in minimal_tex


def test_preamble_contains_fancyhdr(minimal_tex: str) -> None:
    assert r"\usepackage{fancyhdr}" in minimal_tex


def test_preamble_contains_hyperref(minimal_tex: str) -> None:
    assert r"\usepackage" in minimal_tex and "hyperref" in minimal_tex


def test_preamble_contains_amsmath(minimal_tex: str) -> None:
    assert r"\usepackage{amsmath}" in minimal_tex


def test_preamble_contains_graphicx(minimal_tex: str) -> None:
    assert r"\usepackage{graphicx}" in minimal_tex


def test_preamble_contains_booktabs(minimal_tex: str) -> None:
    assert r"\usepackage{booktabs}" in minimal_tex


def test_preamble_contains_tabularx(minimal_tex: str) -> None:
    assert r"\usepackage{tabularx}" in minimal_tex


def test_preamble_contains_biblatex(minimal_tex: str) -> None:
    assert r"\usepackage[backend=biber" in minimal_tex


def test_preamble_addbibresource_uses_bib_filename(minimal_tex: str) -> None:
    assert r"\addbibresource{references.bib}" in minimal_tex


def test_preamble_pagestyle_fancy(minimal_tex: str) -> None:
    assert r"\pagestyle{fancy}" in minimal_tex


def test_preamble_fancyhead_present(minimal_tex: str) -> None:
    assert r"\fancyhead" in minimal_tex


def test_preamble_fancyfoot_present(minimal_tex: str) -> None:
    assert r"\fancyfoot" in minimal_tex


def test_document_contains_maketitle(minimal_tex: str) -> None:
    assert r"\maketitle" in minimal_tex


def test_document_contains_tableofcontents(minimal_tex: str) -> None:
    assert r"\tableofcontents" in minimal_tex


def test_document_contains_printbibliography(minimal_tex: str) -> None:
    assert r"\printbibliography" in minimal_tex


def test_document_has_begin_and_end(minimal_tex: str) -> None:
    assert r"\begin{document}" in minimal_tex
    assert r"\end{document}" in minimal_tex


def test_config_topic_in_title(minimal_tex: str) -> None:
    assert "Machine Learning Study" in minimal_tex


def test_config_author_in_output(minimal_tex: str) -> None:
    assert "Jane Doe" in minimal_tex


def test_config_date_in_output(minimal_tex: str) -> None:
    assert "2026-06-09" in minimal_tex


def test_config_course_in_output(minimal_tex: str) -> None:
    assert "AI Agents MSC" in minimal_tex


def test_config_lecturer_in_output(minimal_tex: str) -> None:
    assert "Dr. Yoram Segal" in minimal_tex


# ---------------------------------------------------------------------------
# 2. generate_tex — body conversion
# ---------------------------------------------------------------------------


def test_h1_becomes_section(full_tex: str) -> None:
    assert r"\section{Abstract}" in full_tex


def test_h2_becomes_subsection(full_tex: str) -> None:
    assert r"\subsection{Background}" in full_tex


def test_h3_becomes_subsubsection(full_tex: str) -> None:
    assert r"\subsubsection{Details}" in full_tex


def test_bold_becomes_textbf(full_tex: str) -> None:
    assert r"\textbf{recurrent}" in full_tex


def test_italic_becomes_textit(full_tex: str) -> None:
    assert r"\textit{convolutions}" in full_tex


def test_inline_code_becomes_texttt(full_tex: str) -> None:
    assert r"\texttt{code}" in full_tex


def test_citation_becomes_cite(full_tex: str) -> None:
    assert r"\cite{vaswani2017}" in full_tex


def test_hyperlink_becomes_href(full_tex: str) -> None:
    assert r"\href{https://openai.com}{OpenAI}" in full_tex


def test_formula_comment_becomes_equation_env(full_tex: str) -> None:
    assert r"\begin{equation}" in full_tex
    assert r"\end{equation}" in full_tex


def test_formula_content_preserved(full_tex: str) -> None:
    assert r"\nabla" in full_tex
    assert r"\frac" in full_tex


def test_pipe_table_becomes_tabularx(full_tex: str) -> None:
    assert r"\begin{tabularx}" in full_tex


def test_table_has_booktabs_rules(full_tex: str) -> None:
    assert r"\toprule" in full_tex
    assert r"\midrule" in full_tex
    assert r"\bottomrule" in full_tex


def test_table_header_cells_are_bold(full_tex: str) -> None:
    assert r"\textbf{Model}" in full_tex


def test_image_becomes_includegraphics(full_tex: str) -> None:
    assert r"\includegraphics" in full_tex
    assert "assets/graph.png" in full_tex


def test_image_wrapped_in_figure_env(full_tex: str) -> None:
    assert r"\begin{figure}" in full_tex
    assert r"\end{figure}" in full_tex
    assert r"\caption" in full_tex
    assert r"\label{fig:" in full_tex


# ---------------------------------------------------------------------------
# 3. generate_tex — error handling and file output
# ---------------------------------------------------------------------------


def test_missing_abstract_raises_error(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    md = "# Introduction\nHi.\n# Conclusion\nBye.\n"
    with pytest.raises(LaTeXGenerationError, match="abstract"):
        compiler.generate_tex(md, cfg)


def test_missing_introduction_raises_error(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    md = "# Abstract\nA.\n# Conclusion\nC.\n"
    with pytest.raises(LaTeXGenerationError, match="introduction"):
        compiler.generate_tex(md, cfg)


def test_missing_conclusion_raises_error(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    md = "# Abstract\nA.\n# Introduction\nI.\n"
    with pytest.raises(LaTeXGenerationError, match="conclusion"):
        compiler.generate_tex(md, cfg)


def test_tex_file_written_to_output_dir(
    compiler: LaTeXCompiler, cfg: ArticleConfig, tmp_path: Path
) -> None:
    compiler.generate_tex(_MINIMAL_MD, cfg)
    assert (tmp_path / "article.tex").exists()


def test_generate_tex_return_matches_written_file(
    compiler: LaTeXCompiler, cfg: ArticleConfig, tmp_path: Path
) -> None:
    tex = compiler.generate_tex(_MINIMAL_MD, cfg)
    written = (tmp_path / "article.tex").read_text(encoding="utf-8")
    assert tex == written


# ---------------------------------------------------------------------------
# 4. generate_bib — entry formatting
# ---------------------------------------------------------------------------


def test_article_entry_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF], cfg)
    assert "@article{vaswani2017," in bib


def test_book_entry_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_BOOK_REF], cfg)
    assert "@book{bishop2006," in bib


def test_inproceedings_entry_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_INPROC_REF], cfg)
    assert "@inproceedings{devlin2019," in bib


def test_misc_entry_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_MISC_REF], cfg)
    assert "@misc{openai2023," in bib


def test_article_journal_field_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF], cfg)
    assert "journal" in bib
    assert "Advances in Neural Information Processing Systems" in bib


def test_article_volume_field_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF], cfg)
    assert "volume" in bib


def test_book_publisher_field_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_BOOK_REF], cfg)
    assert "publisher" in bib
    assert "Springer" in bib


def test_inproc_booktitle_field_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_INPROC_REF], cfg)
    assert "booktitle" in bib
    assert "NAACL-HLT" in bib


def test_misc_url_field_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_MISC_REF], cfg)
    assert "url" in bib
    assert "https://openai.com/research/gpt-4" in bib


def test_optional_doi_included_when_set(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    ref = Reference(
        key="x", entry_type="article",
        author="A", title="T", journal="J", year="2020", volume="1",
        doi="10.1234/test",
    )
    bib = compiler.generate_bib([ref], cfg)
    assert "doi" in bib
    assert "10.1234/test" in bib


def test_empty_optional_fields_not_written(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF], cfg)
    assert "booktitle" not in bib     # @article has no booktitle
    assert "publisher" not in bib


def test_header_comment_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF], cfg)
    assert "% Generated by LaTeXCompiler" in bib


def test_multiple_entries_all_present(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([_ARTICLE_REF, _BOOK_REF, _INPROC_REF, _MISC_REF], cfg)
    assert "@article{vaswani2017," in bib
    assert "@book{bishop2006," in bib
    assert "@inproceedings{devlin2019," in bib
    assert "@misc{openai2023," in bib


def test_empty_reference_list_no_error(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bib = compiler.generate_bib([], cfg)
    assert "% Generated by LaTeXCompiler" in bib


def test_bib_file_written_to_output_dir(
    compiler: LaTeXCompiler, cfg: ArticleConfig, tmp_path: Path
) -> None:
    compiler.generate_bib([_ARTICLE_REF], cfg)
    assert (tmp_path / "references.bib").exists()


# ---------------------------------------------------------------------------
# 5. generate_bib — error handling
# ---------------------------------------------------------------------------


def test_article_missing_journal_raises(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="x", entry_type="article",
                    author="A", title="T", year="2020", volume="1")
    with pytest.raises(BibGenerationError, match="journal"):
        compiler.generate_bib([bad], cfg)


def test_article_missing_volume_raises(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="x", entry_type="article",
                    author="A", title="T", year="2020", journal="J")
    with pytest.raises(BibGenerationError, match="volume"):
        compiler.generate_bib([bad], cfg)


def test_book_missing_publisher_raises(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="x", entry_type="book",
                    author="A", title="T", year="2020")
    with pytest.raises(BibGenerationError, match="publisher"):
        compiler.generate_bib([bad], cfg)


def test_misc_missing_url_raises(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="x", entry_type="misc",
                    author="A", title="T", year="2020")
    with pytest.raises(BibGenerationError, match="url"):
        compiler.generate_bib([bad], cfg)


def test_unknown_entry_type_raises(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="x", entry_type="thesis",
                    author="A", title="T", year="2020")
    with pytest.raises(BibGenerationError, match="unknown entry type"):
        compiler.generate_bib([bad], cfg)


def test_error_message_contains_key(compiler: LaTeXCompiler, cfg: ArticleConfig) -> None:
    bad = Reference(key="my_bad_key", entry_type="article",
                    author="A", title="T", year="2020")
    with pytest.raises(BibGenerationError, match="my_bad_key"):
        compiler.generate_bib([bad], cfg)


# ---------------------------------------------------------------------------
# 6. compile — success path
# ---------------------------------------------------------------------------


def test_compile_returns_compilation_result(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert isinstance(result, CompilationResult)


def test_compile_success_flag_true(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.success is True


def test_compile_passes_completed_is_4(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.passes_completed == 4


def test_compile_pdf_path_set_on_success(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.pdf_path == pdf_file


def test_compile_log_path_set(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.log_path == clean_log


def test_compile_no_errors_on_clean_run(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.errors == []


def test_compile_duration_is_positive(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.duration_seconds >= 0


def test_compile_calls_subprocess_four_times(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch(
        "article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok
    ) as mock_run:
        compiler.compile(str(tex_file), "")
    assert mock_run.call_count == 4


def test_compile_xelatex_called_with_nonstopmode(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch(
        "article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok
    ) as mock_run:
        compiler.compile(str(tex_file), "")
    xelatex_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == LATEX_ENGINE
    ]
    assert len(xelatex_calls) == 3
    for c in xelatex_calls:
        assert "--interaction=nonstopmode" in c.args[0]


def test_compile_biber_called_with_stem(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch(
        "article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok
    ) as mock_run:
        compiler.compile(str(tex_file), "")
    biber_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == BIBER_EXECUTABLE
    ]
    assert len(biber_calls) == 1
    assert biber_calls[0].args[0][1] == "article"   # stem of article.tex


# ---------------------------------------------------------------------------
# 7. compile — error paths
# ---------------------------------------------------------------------------


def test_compile_raises_on_missing_tex_file(compiler: LaTeXCompiler) -> None:
    with pytest.raises(FileNotFoundError):
        compiler.compile("/nonexistent/article.tex", "")


def test_compile_raises_compilation_error_on_bang_line(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    log = tmp_path / "article.log"
    log.write_text("! Undefined control sequence.\nl.5 \\badcmd", encoding="utf-8")
    mock_fail = MagicMock(returncode=1, stdout="", stderr="")
    with patch(
        "article_generator.services.latex_compiler.subprocess.run", return_value=mock_fail
    ):
        with pytest.raises(CompilationError):
            compiler.compile(str(tex_file), "")


def test_compilation_error_carries_result(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    log = tmp_path / "article.log"
    log.write_text("! Undefined control sequence.", encoding="utf-8")
    mock_fail = MagicMock(returncode=1, stdout="", stderr="")
    with patch(
        "article_generator.services.latex_compiler.subprocess.run", return_value=mock_fail
    ):
        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result is not None
    assert "! Undefined control sequence." in exc_info.value.result.errors


def test_passes_completed_0_when_pass1_fails(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("No bang.", encoding="utf-8")
    with patch(
        "article_generator.services.latex_compiler.subprocess.run",
        return_value=MagicMock(returncode=1, stdout="", stderr=""),
    ):
        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result.passes_completed == 0


def test_passes_completed_1_when_biber_fails(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("No bang.", encoding="utf-8")
    _n = [0]

    def _side(*args, **kwargs):  # type: ignore[no-untyped-def]
        _n[0] += 1
        return MagicMock(returncode=1 if _n[0] == 2 else 0, stdout="biber err", stderr="")

    with patch("article_generator.services.latex_compiler.subprocess.run", side_effect=_side):
        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result.passes_completed == 1


def test_passes_completed_2_when_pass3_fails(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("No bang.", encoding="utf-8")
    _n = [0]

    def _side(*args, **kwargs):  # type: ignore[no-untyped-def]
        _n[0] += 1
        return MagicMock(returncode=1 if _n[0] == 3 else 0, stdout="", stderr="")

    with patch("article_generator.services.latex_compiler.subprocess.run", side_effect=_side):
        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result.passes_completed == 2


def test_passes_completed_3_when_pass4_fails(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("No bang.", encoding="utf-8")
    _n = [0]

    def _side(*args, **kwargs):  # type: ignore[no-untyped-def]
        _n[0] += 1
        return MagicMock(returncode=1 if _n[0] == 4 else 0, stdout="", stderr="")

    with patch("article_generator.services.latex_compiler.subprocess.run", side_effect=_side):
        with pytest.raises(CompilationError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result.passes_completed == 3


def test_compilation_timeout_raises_timeout_error(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("", encoding="utf-8")
    with patch(
        "article_generator.services.latex_compiler.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=LATEX_ENGINE, timeout=120),
    ):
        with pytest.raises(CompilationTimeoutError):
            compiler.compile(str(tex_file), "")


def test_compilation_timeout_is_subclass_of_compilation_error() -> None:
    assert issubclass(CompilationTimeoutError, CompilationError)


def test_timeout_error_carries_result(
    compiler: LaTeXCompiler, tex_file: Path, tmp_path: Path
) -> None:
    (tmp_path / "article.log").write_text("", encoding="utf-8")
    with patch(
        "article_generator.services.latex_compiler.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=LATEX_ENGINE, timeout=120),
    ):
        with pytest.raises(CompilationTimeoutError) as exc_info:
            compiler.compile(str(tex_file), "")
    assert exc_info.value.result is not None


# ---------------------------------------------------------------------------
# 8. compile — warning detection
# ---------------------------------------------------------------------------


def test_overfull_hbox_detected_as_warning(
    compiler: LaTeXCompiler,
    tex_file: Path,
    tmp_path: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    (tmp_path / "article.log").write_text(
        r"Overfull \hbox (5.0pt too wide) in paragraph at lines 10--11.", encoding="utf-8"
    )
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert any("Overfull" in w for w in result.warnings)


def test_undefined_citation_detected_as_warning(
    compiler: LaTeXCompiler,
    tex_file: Path,
    tmp_path: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    (tmp_path / "article.log").write_text(
        "LaTeX Warning: Citation 'missing' on page 1 undefined on input line 5.",
        encoding="utf-8",
    )
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert any("undefined on input line" in w for w in result.warnings)


def test_hyperref_warning_detected(
    compiler: LaTeXCompiler,
    tex_file: Path,
    tmp_path: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    (tmp_path / "article.log").write_text(
        "Package hyperref Warning: Token not allowed in a PDF string.",
        encoding="utf-8",
    )
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert any("hyperref" in w for w in result.warnings)


def test_clean_log_has_no_warnings(
    compiler: LaTeXCompiler,
    tex_file: Path,
    clean_log: Path,
    pdf_file: Path,
    mock_ok: MagicMock,
) -> None:
    with patch("article_generator.services.latex_compiler.subprocess.run", return_value=mock_ok):
        result = compiler.compile(str(tex_file), "")
    assert result.warnings == []
