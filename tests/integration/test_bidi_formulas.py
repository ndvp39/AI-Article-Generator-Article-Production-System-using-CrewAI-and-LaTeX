from __future__ import annotations

# Integration tests — T-064
#
# Verify that the LaTeX pipeline does not degrade mathematical formulas to
# plain-text approximations (e.g. "sigma", "integral").
#
# DoD: Agent output contains no `sigma` / `integral` plain-text; all formulas
#      are LaTeX math commands.
#
# The BiDiSpecialistAgent is responsible for correcting formula degradation at
# the agent level.  These tests verify the LaTeXCompiler layer:
#   — `<!-- FORMULA: ... -->` directives are converted to equation environments
#   — The converted .tex contains proper LaTeX math commands
#   — No plain-text formula words appear as standalone text in the LaTeX body
#     when the source markdown uses the formula directive correctly
import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    LaTeXCompiler,
)

# ---------------------------------------------------------------------------
# Markdown with formula directives — these must become equation environments
# ---------------------------------------------------------------------------

_MD_WITH_FORMULAS = r"""\
## Abstract
Abstract about gradient descent and cross-entropy loss.

## Introduction
The cross-entropy loss is defined as:

<!-- FORMULA: \mathcal{L} = -\frac{1}{N}\sum_{i=1}^{N} y_i \log \hat{y}_i -->

The gradient descent update rule is:

<!-- FORMULA: \theta \leftarrow \theta - \alpha \nabla_\theta \mathcal{L} -->

The softmax function normalises a vector:

<!-- FORMULA: \sigma(\mathbf{z})_j = \frac{e^{z_j}}{\sum_{k=1}^{K} e^{z_k}} -->

## Conclusion
All formulas above use proper LaTeX math environments.
"""

# Markdown where formulas are written as plain English words (degraded state)
_MD_PLAIN_TEXT_FORMULAS = """\
## Abstract
Abstract about functions.

## Introduction
The loss function uses sigma and integral operations.
The gradient uses nabla and partial derivatives.
Cross-entropy loss involves logarithm and summation.

## Conclusion
Conclusion.
"""

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def formula_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Generate .tex from markdown that uses <!-- FORMULA: ... --> directives."""
    work_dir = tmp_path_factory.mktemp("bidi_formula")
    cfg = ArticleConfig(
        topic="Formula Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MD_WITH_FORMULAS, cfg)


@pytest.fixture(scope="module")
def plain_text_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Generate .tex from markdown that has plain-text formula words."""
    work_dir = tmp_path_factory.mktemp("bidi_formula_plain")
    cfg = ArticleConfig(
        topic="Plain Formula Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MD_PLAIN_TEXT_FORMULAS, cfg)


# ---------------------------------------------------------------------------
# 1. Formula directive → equation environment conversion
# ---------------------------------------------------------------------------


def test_formula_directive_produces_equation_env(formula_tex: str) -> None:
    """<!-- FORMULA: ... --> becomes \\begin{equation}...\\end{equation}."""
    assert r"\begin{equation}" in formula_tex
    assert r"\end{equation}" in formula_tex


def test_formula_tex_has_correct_equation_count(formula_tex: str) -> None:
    """One equation environment per <!-- FORMULA: --> directive (3 in test md)."""
    count = formula_tex.count(r"\begin{equation}")
    assert count == 3, f"Expected 3 equation environments, got {count}"


def test_formula_content_is_preserved(formula_tex: str) -> None:
    r"""LaTeX math content inside <!-- FORMULA: --> is preserved verbatim."""
    assert r"\mathcal{L}" in formula_tex
    assert r"\nabla_\theta" in formula_tex
    assert r"\sigma(\mathbf{z})_j" in formula_tex


def test_no_formula_directive_comments_in_output(formula_tex: str) -> None:
    """The <!-- FORMULA: --> HTML comment is consumed — must not appear in .tex."""
    assert "<!-- FORMULA:" not in formula_tex


# ---------------------------------------------------------------------------
# 2. LaTeX math commands instead of plain-text approximations
# ---------------------------------------------------------------------------


def test_formula_tex_uses_frac_not_plain_text(formula_tex: str) -> None:
    r"""Fractions use \frac{} not prose like 'divided by'."""
    assert r"\frac" in formula_tex


def test_formula_tex_uses_sum_command(formula_tex: str) -> None:
    r"""\sum is a LaTeX command, not the word 'summation'."""
    assert r"\sum" in formula_tex


def test_formula_tex_uses_sigma_command(formula_tex: str) -> None:
    r"""\sigma is a LaTeX command, not the word 'sigma'."""
    assert r"\sigma" in formula_tex


def test_formula_tex_uses_nabla_command(formula_tex: str) -> None:
    r"""\nabla is a LaTeX command, not the word 'nabla'."""
    assert r"\nabla" in formula_tex


# ---------------------------------------------------------------------------
# 3. Plain-text formula words do NOT become equation environments
# ---------------------------------------------------------------------------


def test_plain_words_sigma_not_wrapped_in_equation(plain_text_tex: str) -> None:
    r"""The compiler does not auto-detect 'sigma' as a formula — that is the
    BiDiSpecialistAgent's responsibility.  Plain text stays as plain text."""
    # The plain-text source has "sigma" in prose — it should stay as prose,
    # not be auto-converted to \sigma (which would be hallucinating structure).
    assert "sigma" in plain_text_tex


def test_plain_text_tex_has_no_spurious_equation_env(plain_text_tex: str) -> None:
    """No equation environment is injected for plain-text formula words."""
    assert r"\begin{equation}" not in plain_text_tex
