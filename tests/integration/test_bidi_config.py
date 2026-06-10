from __future__ import annotations

# Integration tests — T-062
#
# Verify that the .tex preamble produced by generate_tex() is correctly
# configured for Hebrew (main/RTL) + English (secondary/LTR) bidirectional
# typesetting via polyglossia.
#
# DoD: preamble contains \usepackage{polyglossia} with Hebrew as MAIN language
#      (\setmainlanguage{hebrew}) and English as secondary language
#      (\setotherlanguage{english}); \setmainlanguage{hebrew} is REQUIRED.
#
# These tests are source-only (no compilation required) and always run.
import json
from pathlib import Path

import pytest

from article_generator.services.latex_compiler import (
    ArticleConfig,
    ArticlePaths,
    LaTeXCompiler,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_MD = """\
## Abstract
Abstract text.

## Introduction
Introduction text.

## Conclusion
Conclusion text.
"""


@pytest.fixture(scope="module")
def preamble_tex(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return the full .tex source produced by generate_tex()."""
    work_dir = tmp_path_factory.mktemp("bidi_config")
    cfg = ArticleConfig(
        topic="BiDi Config Test",
        author="Test Author",
        date="2026-06-09",
        course="Test Course",
        lecturer="Prof Test",
        paths=ArticlePaths(output_dir=work_dir, bib_filename="references.bib"),
    )
    return LaTeXCompiler().generate_tex(_MINIMAL_MD, cfg)


# ---------------------------------------------------------------------------
# 1. Polyglossia package
# ---------------------------------------------------------------------------


def test_preamble_has_polyglossia_package(preamble_tex: str) -> None:
    """`\\usepackage{polyglossia}` is present — required for Hebrew RTL support."""
    assert r"\usepackage{polyglossia}" in preamble_tex


def test_no_babel_conflicts(preamble_tex: str) -> None:
    """babel must not be loaded alongside polyglossia — they conflict."""
    assert r"\usepackage{babel}" not in preamble_tex


# ---------------------------------------------------------------------------
# 2. Hebrew as main (RTL) language — REQUIRED per T-062 DoD
# ---------------------------------------------------------------------------


def test_preamble_sets_main_language_hebrew(preamble_tex: str) -> None:
    r"""\setmainlanguage{hebrew} declares Hebrew as the document's primary language."""
    assert r"\setmainlanguage{hebrew}" in preamble_tex


def test_preamble_does_not_set_main_language_english(preamble_tex: str) -> None:
    r"""\setmainlanguage{english} would make English the primary language — forbidden."""
    assert r"\setmainlanguage{english}" not in preamble_tex


# ---------------------------------------------------------------------------
# 3. English as secondary (LTR) language
# ---------------------------------------------------------------------------


def test_preamble_sets_other_language_english(preamble_tex: str) -> None:
    r"""\setotherlanguage{english} registers English as the secondary language."""
    assert r"\setotherlanguage{english}" in preamble_tex


def test_preamble_does_not_set_other_language_hebrew(preamble_tex: str) -> None:
    r"""\setotherlanguage{hebrew} would put Hebrew in the secondary slot — forbidden."""
    assert r"\setotherlanguage{hebrew}" not in preamble_tex


# ---------------------------------------------------------------------------
# 4. Ordering — Hebrew must be declared BEFORE English
# ---------------------------------------------------------------------------


def test_setmainlanguage_hebrew_before_setotherlanguage_english(
    preamble_tex: str,
) -> None:
    r"""Hebrew main language is declared before the English secondary language."""
    pos_main  = preamble_tex.find(r"\setmainlanguage{hebrew}")
    pos_other = preamble_tex.find(r"\setotherlanguage{english}")
    assert pos_main != -1 and pos_other != -1
    assert pos_main < pos_other, (
        r"\setmainlanguage{hebrew} must appear before \setotherlanguage{english}"
    )


def test_polyglossia_loaded_before_language_declarations(preamble_tex: str) -> None:
    r"""polyglossia must be loaded before \setmainlanguage / \setotherlanguage."""
    pos_pkg  = preamble_tex.find(r"\usepackage{polyglossia}")
    pos_main = preamble_tex.find(r"\setmainlanguage{hebrew}")
    assert pos_pkg != -1 and pos_main != -1
    assert pos_pkg < pos_main


# ---------------------------------------------------------------------------
# 5. Hebrew font declaration
# ---------------------------------------------------------------------------


def test_preamble_has_hebrew_font_family(preamble_tex: str) -> None:
    r"""\newfontfamily\hebrewfont is required for Hebrew glyph rendering."""
    assert r"\newfontfamily\hebrewfont" in preamble_tex


def test_preamble_hebrew_font_has_script_attribute(preamble_tex: str) -> None:
    """Script=Hebrew attribute ensures correct OpenType glyph selection."""
    assert "Script=Hebrew" in preamble_tex


def test_preamble_specifies_david_clm_font(preamble_tex: str) -> None:
    """David CLM is the designated Hebrew font for this project."""
    assert "David CLM" in preamble_tex


# ---------------------------------------------------------------------------
# 6. Engine must be lualatex-compatible (not pdflatex)
# ---------------------------------------------------------------------------


def test_preamble_documentclass_is_article(preamble_tex: str) -> None:
    assert r"\documentclass" in preamble_tex and "article" in preamble_tex


def test_preamble_no_pdflatex_only_packages(preamble_tex: str) -> None:
    """pdflatex-only packages (inputenc with utf8 in pdflatex mode) must not appear."""
    assert r"\usepackage[utf8]{inputenc}" not in preamble_tex


# ---------------------------------------------------------------------------
# 7. config/setup.json alignment
# ---------------------------------------------------------------------------


def test_config_language_is_hebrew() -> None:
    """setup.json article.language must match the preamble's main language."""
    config_path = Path("config/setup.json")
    if not config_path.exists():
        pytest.skip("config/setup.json not found")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    assert cfg["setup"]["article"]["language"] == "hebrew"


def test_config_bidi_language_is_english() -> None:
    """setup.json article.bidi_language must match the preamble's secondary language."""
    config_path = Path("config/setup.json")
    if not config_path.exists():
        pytest.skip("config/setup.json not found")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    assert cfg["setup"]["article"]["bidi_language"] == "english"


def test_config_latex_engine_is_xelatex() -> None:
    """setup.json latex.engine must be xelatex — required for bidi + polyglossia + Hebrew."""
    config_path = Path("config/setup.json")
    if not config_path.exists():
        pytest.skip("config/setup.json not found")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    assert cfg["setup"]["latex"]["engine"] == "xelatex"
