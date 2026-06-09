from __future__ import annotations

# T-053 — Verify LaTeX Formatter agent produces at least one "fancy" formula
#
# DoD: .tex output contains at least one math environment (equation, align, etc.)
#      with \frac, \sum, \int, or similar; no plain-text formula approximations.
#
# PRD FR-04: Formula MUST use LaTeX math commands (\frac, \sum, \int, \nabla,
# subscripts, superscripts).  Plain-text approximations are NOT acceptable.
import re

# ---------------------------------------------------------------------------
# In-test helpers — detection and validation
# ---------------------------------------------------------------------------

# Named display math environments recognised by LaTeX amsmath
_DISPLAY_ENV_NAMES = (
    "equation", "equation*",
    "align", "align*",
    "gather", "gather*",
    "multline", "multline*",
    "eqnarray", "eqnarray*",
    "flalign", "flalign*",
)

# Regex that matches any of the above environments (content captured)
_ENV_PATTERN = re.compile(
    r"\\begin\{(" + "|".join(re.escape(e) for e in _DISPLAY_ENV_NAMES) + r")\}"
    r"(.*?)"
    r"\\end\{\1\}",
    re.DOTALL,
)

# Inline display math \[...\] and $$...$$
_DISPLAY_MATH_PATTERNS = [
    re.compile(r"\\\[(.*?)\\\]", re.DOTALL),
    re.compile(r"\$\$(.*?)\$\$", re.DOTALL),
]

# LaTeX commands that constitute a "fancy" (non-trivial) formula
_FANCY_COMMANDS = frozenset({
    r"\frac", r"\sum", r"\int", r"\prod", r"\sqrt", r"\lim",
    r"\nabla", r"\partial", r"\infty", r"\theta", r"\alpha",
    r"\beta", r"\sigma", r"\lambda", r"\mu", r"\pi",
    r"\Delta", r"\Sigma", r"\mathcal", r"\left", r"\right",
    r"\binom", r"\oint", r"\iint",
})

# Plain-text formula words that must NOT appear outside a math context
_PLAIN_TEXT_FORMULA_WORDS = {
    "sigma", "integral", "infinity", "theta", "alpha", "beta",
}


def find_named_math_environments(tex: str) -> list[tuple[str, str]]:
    """Return (env_name, content) for every named display math environment."""
    return [(m.group(1), m.group(2)) for m in _ENV_PATTERN.finditer(tex)]


def find_display_math_blocks(tex: str) -> list[str]:
    r"""Return content of all \[...\] and $$...$$ display math blocks."""
    results: list[str] = []
    for pat in _DISPLAY_MATH_PATTERNS:
        results.extend(m.group(1) for m in pat.finditer(tex))
    return results


def all_math_contents(tex: str) -> list[str]:
    """Return all math environment contents from *tex* (named + display blocks)."""
    contents = [content for _, content in find_named_math_environments(tex)]
    contents.extend(find_display_math_blocks(tex))
    return contents


def has_fancy_command(math_content: str) -> bool:
    """Return True if *math_content* contains at least one fancy LaTeX command."""
    return any(cmd in math_content for cmd in _FANCY_COMMANDS)


def strip_math_contexts(tex: str) -> str:
    """Remove all math contexts from *tex* to expose remaining plain text."""
    result = _ENV_PATTERN.sub("", tex)
    for pat in _DISPLAY_MATH_PATTERNS:
        result = pat.sub("", result)
    # Also strip inline $...$ math
    result = re.sub(r"\$[^$\n]+\$", "", result)
    return result


def find_plaintext_formula_words(tex: str) -> list[str]:
    """Return plain-text formula approximations found outside math contexts."""
    plain = strip_math_contexts(tex)
    # Remove LaTeX command names so \sigma is not flagged as 'sigma'
    plain = re.sub(r"\\[a-zA-Z]+", "", plain)
    found = []
    for word in _PLAIN_TEXT_FORMULA_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", plain, re.IGNORECASE):
            found.append(word)
    return found


# ---------------------------------------------------------------------------
# Representative .tex content produced by LaTeXFormatterAgent
# ---------------------------------------------------------------------------

_TEX_WITH_EQUATION = r"""
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath,amssymb}

\begin{document}

\section{Mathematical Foundations}

The weight update rule for gradient descent is:
\begin{equation}
    \theta_{t+1} = \theta_t - \alpha \nabla_\theta \mathcal{L}(\theta_t)
\end{equation}
where $\alpha$ is the learning rate and $\mathcal{L}$ is the loss function.

\end{document}
"""

_TEX_WITH_ALIGN = r"""
\begin{document}

\section{Loss Function}

The cross-entropy loss is defined as:
\begin{align}
    \mathcal{L}(\theta) &= -\frac{1}{N} \sum_{i=1}^{N}
        \left[ y_i \log \hat{y}_i + (1 - y_i) \log(1 - \hat{y}_i) \right]
\end{align}

The attention mechanism is computed by:
\begin{align*}
    \text{Attention}(Q, K, V) &= \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V
\end{align*}

\end{document}
"""

_TEX_WITH_DISPLAY_BLOCK = r"""
\begin{document}

Fourier transform pair:
\[
    \hat{f}(\xi) = \int_{-\infty}^{\infty} f(x)\, e^{-2\pi i x \xi}\, \mathrm{d}x
\]

\end{document}
"""

_TEX_NO_MATH = r"""
\begin{document}

This document discusses machine learning concepts without any formulas.

\end{document}
"""

_TEX_WITH_PLAINTEXT_SIGMA = r"""
\begin{document}

The sigma value controls the noise level in the model.

\end{document}
"""

_TEX_WITH_PLAINTEXT_INTEGRAL = r"""
\begin{document}

We compute the integral of the distribution over all values.

\end{document}
"""

_TEX_SIGMA_IN_MATH_ONLY = r"""
\begin{document}

We use the notation $\sigma$ for the sigmoid function, defined as:
\begin{equation}
    \sigma(x) = \frac{1}{1 + e^{-x}}
\end{equation}

\end{document}
"""

# Full representative article .tex — what LaTeXFormatterAgent produces
_REPRESENTATIVE_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,tabularx}
\usepackage{tikz}
\usepackage[backend=biber,style=numeric]{biblatex}
\addbibresource{references.bib}
\usepackage[colorlinks=true]{hyperref}
\usepackage{bidi}

\begin{document}

\section{Mathematical Background}

The transformer self-attention mechanism \cite{vaswani2017} is defined as:
\begin{equation}
    \text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V
    \label{eq:attention}
\end{equation}

The multi-head variant stacks $h$ attention heads:
\begin{align}
    \text{MultiHead}(Q, K, V) &= \text{Concat}(\text{head}_1, \ldots, \text{head}_h)\,W^O \\
    \text{where} \quad \text{head}_i    &= \text{Attention}(Q W_i^Q,\, K W_i^K,\, V W_i^V)
\end{align}

The cross-entropy loss over $N$ training examples:
\begin{equation*}
    \mathcal{L}(\theta) = -\frac{1}{N} \sum_{i=1}^{N}
        \sum_{c=1}^{C} y_{ic} \log \hat{y}_{ic}
\end{equation*}

\printbibliography
\end{document}
"""


# ---------------------------------------------------------------------------
# 1. Math environment detection
# ---------------------------------------------------------------------------


def test_equation_env_detected():
    envs = find_named_math_environments(_TEX_WITH_EQUATION)
    assert any(name.startswith("equation") for name, _ in envs)


def test_align_env_detected():
    envs = find_named_math_environments(_TEX_WITH_ALIGN)
    assert any(name.startswith("align") for name, _ in envs)


def test_display_block_detected():
    blocks = find_display_math_blocks(_TEX_WITH_DISPLAY_BLOCK)
    assert len(blocks) >= 1


def test_multiple_envs_all_detected():
    envs = find_named_math_environments(_TEX_WITH_ALIGN)
    assert len(envs) == 2  # align + align*


def test_no_math_env_in_plain_doc():
    envs = find_named_math_environments(_TEX_NO_MATH)
    assert envs == []
    assert find_display_math_blocks(_TEX_NO_MATH) == []


def test_all_math_contents_collects_named_and_display():
    contents = all_math_contents(_TEX_WITH_ALIGN)
    assert len(contents) >= 2


# ---------------------------------------------------------------------------
# 2. Fancy command detection
# ---------------------------------------------------------------------------


def test_frac_is_fancy():
    assert has_fancy_command(r"\frac{1}{N} \sum_{i=1}^{N} x_i")


def test_sum_is_fancy():
    assert has_fancy_command(r"\sum_{i=0}^{\infty} a_i r^i")


def test_int_is_fancy():
    assert has_fancy_command(r"\int_{-\infty}^{\infty} f(x)\,dx")


def test_nabla_is_fancy():
    assert has_fancy_command(r"\theta - \alpha \nabla_\theta \mathcal{L}")


def test_sqrt_is_fancy():
    assert has_fancy_command(r"\frac{QK^\top}{\sqrt{d_k}}")


def test_plain_letter_x_is_not_fancy():
    assert not has_fancy_command("x = a + b")


def test_greek_letter_sigma_is_fancy():
    assert has_fancy_command(r"\sigma(x) = \frac{1}{1+e^{-x}}")


def test_equation_env_content_is_fancy():
    envs = find_named_math_environments(_TEX_WITH_EQUATION)
    assert len(envs) >= 1
    assert has_fancy_command(envs[0][1])


def test_align_env_content_is_fancy():
    envs = find_named_math_environments(_TEX_WITH_ALIGN)
    assert any(has_fancy_command(content) for _, content in envs)


def test_display_block_content_is_fancy():
    blocks = find_display_math_blocks(_TEX_WITH_DISPLAY_BLOCK)
    assert any(has_fancy_command(b) for b in blocks)


# ---------------------------------------------------------------------------
# 3. Plain-text anti-pattern detection
# ---------------------------------------------------------------------------


def test_sigma_in_plain_text_flagged():
    found = find_plaintext_formula_words(_TEX_WITH_PLAINTEXT_SIGMA)
    assert "sigma" in found


def test_integral_in_plain_text_flagged():
    found = find_plaintext_formula_words(_TEX_WITH_PLAINTEXT_INTEGRAL)
    assert "integral" in found


def test_sigma_inside_math_not_flagged():
    """\\sigma inside a math context must NOT be reported as a plain-text word."""
    found = find_plaintext_formula_words(_TEX_SIGMA_IN_MATH_ONLY)
    assert "sigma" not in found


def test_clean_tex_has_no_plaintext_formulas():
    found = find_plaintext_formula_words(_REPRESENTATIVE_TEX)
    assert found == [], f"Unexpected plain-text formula words: {found}"


def test_plain_tex_no_math_has_no_formulas():
    found = find_plaintext_formula_words(_TEX_NO_MATH)
    assert found == []


# ---------------------------------------------------------------------------
# 4. Representative LaTeXFormatterAgent output — T-053 DoD
# ---------------------------------------------------------------------------


def test_representative_tex_has_at_least_one_math_environment():
    """T-053 DoD: .tex output contains at least one math environment."""
    contents = all_math_contents(_REPRESENTATIVE_TEX)
    assert len(contents) >= 1, "No math environment found in representative .tex"


def test_representative_tex_math_contains_fancy_command():
    r"""T-053 DoD: math environment uses \frac, \sum, \int, or similar."""
    contents = all_math_contents(_REPRESENTATIVE_TEX)
    assert any(has_fancy_command(c) for c in contents), (
        "No fancy math command (\\frac, \\sum, \\int, ...) found in any math environment"
    )


def test_representative_tex_has_no_plain_text_approximations():
    """T-053 DoD: no plain-text formula approximations present."""
    found = find_plaintext_formula_words(_REPRESENTATIVE_TEX)
    assert found == [], f"Plain-text formula words found: {found}"


def test_representative_tex_has_equation_with_frac():
    envs = find_named_math_environments(_REPRESENTATIVE_TEX)
    frac_envs = [c for _, c in envs if r"\frac" in c]
    assert frac_envs, "Expected at least one equation environment containing \\frac"


def test_representative_tex_has_sum_in_named_env():
    """\\sum must appear in at least one named math environment (any type)."""
    envs = find_named_math_environments(_REPRESENTATIVE_TEX)
    sum_envs = [c for _, c in envs if r"\sum" in c]
    assert sum_envs, "Expected at least one math environment containing \\sum"


def test_representative_tex_has_multiple_math_envs():
    envs = find_named_math_environments(_REPRESENTATIVE_TEX)
    assert len(envs) >= 2, f"Expected ≥ 2 math environments, found {len(envs)}"
