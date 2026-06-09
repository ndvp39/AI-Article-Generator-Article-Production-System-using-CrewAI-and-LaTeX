from __future__ import annotations

# Integration tests — T-051
#
# Verify that at least one image asset is present in assets/ after GraphRunner
# execution and that the resulting path is valid for use in a LaTeX
# \includegraphics command.
#
# DoD: assets/ contains at least one image file; LaTeX \includegraphics path is valid.
# No API keys required.  Skipped automatically if matplotlib is not installed.
import re

import pytest

from article_generator.services.graph_runner import GraphResult, GraphRunner

pytest.importorskip("matplotlib")  # skip whole module if matplotlib absent

# ---------------------------------------------------------------------------
# Sample graph code (minimal — fast subprocess execution)
# ---------------------------------------------------------------------------

_SIMPLE_CODE = """\
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(5, 3))
ax.plot([1, 2, 3, 4], [0.80, 0.65, 0.45, 0.25], linewidth=2, color="steelblue")
ax.set_xlabel("Epoch")
ax.set_ylabel("Loss")
ax.set_title("Sample Graph")
"""

# Characters that LaTeX treats specially inside a path argument — must be absent
_LATEX_SPECIAL = re.compile(r"[#$%&{}^~\\]")

# Supported extensions that LaTeX's graphicx package accepts
_EMBEDDABLE_EXTENSIONS = {"png", "pdf", "jpg", "jpeg", "eps"}


# ---------------------------------------------------------------------------
# Module-scoped fixtures — each subprocess runs exactly once per test session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def png_result(tmp_path_factory) -> GraphResult:
    assets = tmp_path_factory.mktemp("assets_png")
    return GraphRunner(assets_dir=assets).run(_SIMPLE_CODE, "graph.png")


@pytest.fixture(scope="module")
def pdf_result(tmp_path_factory) -> GraphResult:
    assets = tmp_path_factory.mktemp("assets_pdf")
    return GraphRunner(assets_dir=assets).run(_SIMPLE_CODE, "graph.pdf")


# ---------------------------------------------------------------------------
# 1. File presence — assets/ must contain the generated image
# ---------------------------------------------------------------------------


def test_png_file_exists_in_assets(png_result):
    assert png_result.output_path.exists()


def test_pdf_file_exists_in_assets(pdf_result):
    assert pdf_result.output_path.exists()


def test_assets_dir_is_non_empty_after_png_run(png_result):
    assert any(png_result.output_path.parent.iterdir())


def test_assets_dir_is_non_empty_after_pdf_run(pdf_result):
    assert any(pdf_result.output_path.parent.iterdir())


def test_png_file_size_is_positive(png_result):
    assert png_result.file_size_bytes > 0


def test_pdf_file_size_is_positive(pdf_result):
    assert pdf_result.file_size_bytes > 0


# ---------------------------------------------------------------------------
# 2. Image format validity — magic bytes confirm the file is a real image
# ---------------------------------------------------------------------------


def test_png_magic_bytes_are_valid(png_result):
    """PNG files must start with the 8-byte PNG signature."""
    header = png_result.output_path.read_bytes()[:8]
    assert header == b"\x89PNG\r\n\x1a\n", f"Bad PNG header: {header!r}"


def test_pdf_magic_bytes_are_valid(pdf_result):
    """PDF files must start with %PDF-."""
    header = pdf_result.output_path.read_bytes()[:4]
    assert header == b"%PDF", f"Bad PDF header: {header!r}"


def test_png_extension_is_embeddable(png_result):
    assert png_result.file_format in _EMBEDDABLE_EXTENSIONS


def test_pdf_extension_is_embeddable(pdf_result):
    assert pdf_result.file_format in _EMBEDDABLE_EXTENSIONS


# ---------------------------------------------------------------------------
# 3. LaTeX path validity — \includegraphics{path} must be well-formed
# ---------------------------------------------------------------------------


def test_png_latex_path_uses_forward_slashes(png_result):
    """LaTeX requires forward slashes on all platforms — no backslashes allowed."""
    latex_path = png_result.output_path.as_posix()
    assert "\\" not in latex_path


def test_pdf_latex_path_uses_forward_slashes(pdf_result):
    latex_path = pdf_result.output_path.as_posix()
    assert "\\" not in latex_path


def test_png_filename_has_no_spaces(png_result):
    """Spaces in path arguments require special quoting in LaTeX — avoid them."""
    assert " " not in png_result.output_path.name


def test_pdf_filename_has_no_spaces(pdf_result):
    assert " " not in pdf_result.output_path.name


def test_png_latex_path_has_no_special_latex_chars(png_result):
    r"""Characters like #, $, %, & etc. must not appear in an \includegraphics path."""
    assert not _LATEX_SPECIAL.search(png_result.output_path.name)


def test_pdf_latex_path_has_no_special_latex_chars(pdf_result):
    assert not _LATEX_SPECIAL.search(pdf_result.output_path.name)


# ---------------------------------------------------------------------------
# 4. \includegraphics snippet assembly — T-051 DoD: path is valid in LaTeX
# ---------------------------------------------------------------------------


def test_png_includegraphics_snippet_is_well_formed(png_result):
    """Build the LaTeX snippet exactly as LaTeXFormatterAgent would emit it."""
    posix_path = png_result.output_path.as_posix()
    snippet = (
        r"\begin{figure}[htbp]" "\n"
        r"  \centering" "\n"
        f"  \\includegraphics[width=0.85\\textwidth]{{{posix_path}}}\n"
        r"  \caption{Sample graph showing training loss over epochs.}" "\n"
        r"  \label{fig:main_graph}" "\n"
        r"\end{figure}"
    )
    assert r"\includegraphics" in snippet
    assert posix_path in snippet
    assert r"\caption" in snippet
    assert r"\label{fig:" in snippet


def test_pdf_includegraphics_snippet_is_well_formed(pdf_result):
    posix_path = pdf_result.output_path.as_posix()
    snippet = f"\\includegraphics[width=0.85\\textwidth]{{{posix_path}}}"
    assert r"\includegraphics" in snippet
    assert posix_path in snippet
    # path inside braces must have no backslash-escaped chars
    assert "\\" not in posix_path
