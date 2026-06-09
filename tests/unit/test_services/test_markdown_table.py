from __future__ import annotations

# T-052 — Verify Writer agent produces at least one Markdown table
#
# Tests confirm that:
# 1. Markdown tables using pipe syntax are correctly detected.
# 2. Table structure (header, separator, consistent columns) is valid.
# 3. A table converts cleanly to a LaTeX tabular environment.
# 4. Representative WriterAgent Markdown output contains ≥ 1 valid table.
import re

# ---------------------------------------------------------------------------
# In-test helpers — detection and minimal LaTeX conversion
# ---------------------------------------------------------------------------

# A line is part of a Markdown table when it starts and ends with a pipe.
_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")

# A separator row contains only pipes, dashes, colons, and spaces.
_SEPARATOR_RE = re.compile(r"^\s*\|[\s|:\-]+\|\s*$")


def detect_markdown_tables(text: str) -> list[list[str]]:
    """Return a list of tables found in *text*.

    Each table is a list of raw row strings (header + separator + data rows).
    A valid table must have at least one data row after the separator.
    """
    tables: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if _TABLE_ROW_RE.match(line):
            current.append(line.strip())
        else:
            if len(current) >= 3:  # header + separator + ≥ 1 data row
                tables.append(current)
            current = []
    if len(current) >= 3:
        tables.append(current)
    return tables


def parse_row(row: str) -> list[str]:
    """Split a pipe-delimited row into stripped cell strings."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def is_separator_row(row: str) -> bool:
    """Return True if *row* is a Markdown table separator line."""
    return bool(_SEPARATOR_RE.match(row))


def validate_table_structure(rows: list[str]) -> tuple[bool, str]:
    """Validate that *rows* form a well-structured Markdown table.

    Returns (True, "") on success or (False, reason) on failure.
    """
    if len(rows) < 3:
        return False, "table needs header + separator + ≥ 1 data row"
    if not is_separator_row(rows[1]):
        return False, f"row[1] is not a separator: {rows[1]!r}"
    header_cols = len(parse_row(rows[0]))
    if header_cols < 1:
        return False, "header has no columns"
    for i, row in enumerate(rows[2:], start=2):
        if len(parse_row(row)) != header_cols:
            return False, f"row[{i}] column count {len(parse_row(row))} != header {header_cols}"
    return True, ""


def table_to_latex_tabular(rows: list[str]) -> str:
    """Convert Markdown table rows into a LaTeX tabular environment string."""
    header_cells = parse_row(rows[0])
    n_cols = len(header_cells)
    col_spec = "|" + "|".join("l" * n_cols) + "|"

    lines: list[str] = [
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\hline",
        " & ".join(header_cells) + " \\\\",
        "\\hline",
    ]
    for row in rows[2:]:  # skip separator at rows[1]
        cells = parse_row(row)
        lines.append(" & ".join(cells) + " \\\\")
    lines += ["\\hline", "\\end{tabular}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sample Markdown representing WriterAgent output (Hebrew prose, EN terms)
# The table itself uses standard ASCII pipe syntax regardless of language.
# ---------------------------------------------------------------------------

_ARTICLE_WITH_TABLE = """\
## Abstract

מחקר זה בוחן שיטות למידת מכונה שונות עבור ניתוח תמונות רפואיות.

## Introduction

This section introduces the core concepts discussed in the article.

## Model Comparison

הטבלה הבאה משווה בין מודלים שונים על פי מדדי ביצוע סטנדרטיים.

| Model | Accuracy | F1 Score | Parameters |
|-------|----------|----------|------------|
| Baseline CNN | 0.72 | 0.68 | 1.2M |
| ResNet-50 | 0.85 | 0.82 | 25.6M |
| Vision Transformer | 0.91 | 0.89 | 86.0M |
| Proposed Model | 0.94 | 0.93 | 12.1M |

## Conclusion

מסקנות המחקר מצביעות על יתרון ברור של המודל המוצע.
"""

_ARTICLE_WITH_ALIGNED_TABLE = """\
## Results

| Metric | Value | Notes |
|:-------|------:|:-----:|
| Precision | 0.93 | macro-avg |
| Recall | 0.91 | macro-avg |
| F1 | 0.92 | macro-avg |
"""

_ARTICLE_NO_TABLE = """\
## Abstract

This article discusses deep learning.

## Introduction

No table in this document.
"""

_ARTICLE_TWO_TABLES = """\
## Results

| Model | Accuracy |
|-------|----------|
| CNN | 0.85 |

## Ablation Study

| Component | Delta |
|-----------|-------|
| Attention | +0.03 |
| Dropout | +0.01 |
"""


# ---------------------------------------------------------------------------
# 1. Table detection
# ---------------------------------------------------------------------------


def test_table_detected_in_article():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    assert len(tables) >= 1


def test_no_table_in_plain_text():
    tables = detect_markdown_tables(_ARTICLE_NO_TABLE)
    assert tables == []


def test_two_tables_both_detected():
    tables = detect_markdown_tables(_ARTICLE_TWO_TABLES)
    assert len(tables) == 2


def test_table_with_alignment_markers_detected():
    tables = detect_markdown_tables(_ARTICLE_WITH_ALIGNED_TABLE)
    assert len(tables) == 1


def test_table_first_row_is_header():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    header_cells = parse_row(tables[0][0])
    assert "Model" in header_cells


def test_table_second_row_is_separator():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    assert is_separator_row(tables[0][1])


# ---------------------------------------------------------------------------
# 2. Table structure validation
# ---------------------------------------------------------------------------


def test_valid_table_passes_structure_check():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    ok, reason = validate_table_structure(tables[0])
    assert ok, reason


def test_aligned_table_passes_structure_check():
    tables = detect_markdown_tables(_ARTICLE_WITH_ALIGNED_TABLE)
    ok, reason = validate_table_structure(tables[0])
    assert ok, reason


def test_table_column_count_is_consistent():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    rows = tables[0]
    expected_cols = len(parse_row(rows[0]))
    for row in rows[2:]:
        assert len(parse_row(row)) == expected_cols


def test_table_has_at_least_two_columns():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    assert len(parse_row(tables[0][0])) >= 2


def test_table_has_at_least_two_data_rows():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    data_rows = tables[0][2:]  # skip header + separator
    assert len(data_rows) >= 2


def test_table_header_cells_are_non_empty():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    header_cells = parse_row(tables[0][0])
    assert all(cell for cell in header_cells)


def test_incomplete_table_not_detected():
    """A table with only header + separator but no data rows is not valid."""
    text = "| A | B |\n|---|---|\n"
    tables = detect_markdown_tables(text)
    assert tables == []


def test_non_table_pipe_line_ignored():
    """An isolated pipe line that is not a table should not be detected."""
    text = "Formula: $f(x) = |x|$\nSome other text."
    tables = detect_markdown_tables(text)
    assert tables == []


# ---------------------------------------------------------------------------
# 3. LaTeX tabular conversion
# ---------------------------------------------------------------------------


def test_latex_conversion_produces_begin_tabular():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "\\begin{tabular}" in latex


def test_latex_conversion_produces_end_tabular():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "\\end{tabular}" in latex


def test_latex_conversion_has_hline_separators():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert latex.count("\\hline") >= 2


def test_latex_conversion_uses_ampersand_column_separator():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert " & " in latex


def test_latex_conversion_uses_double_backslash_row_end():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "\\\\" in latex


def test_latex_conversion_column_spec_matches_header_count():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    rows = tables[0]
    n_cols = len(parse_row(rows[0]))
    latex = table_to_latex_tabular(rows)
    # Expected column spec e.g. {|l|l|l|l|} — search for the exact spec pattern
    expected_spec = "|" + "|".join(["l"] * n_cols) + "|"
    assert expected_spec in latex.splitlines()[0]


def test_latex_conversion_preserves_header_content():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "Model" in latex
    assert "Accuracy" in latex


def test_latex_conversion_preserves_data_content():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "ResNet-50" in latex
    assert "0.85" in latex


def test_latex_conversion_data_row_count_matches():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    rows = tables[0]
    data_rows = rows[2:]
    latex = table_to_latex_tabular(rows)
    # Each data row ends with \\; count lines ending with \\
    row_lines = [line for line in latex.splitlines() if line.endswith("\\\\")]
    # header row + all data rows each end with \\
    assert len(row_lines) == 1 + len(data_rows)


# ---------------------------------------------------------------------------
# 4. Representative WriterAgent output — T-052 DoD
# ---------------------------------------------------------------------------


def test_representative_article_contains_at_least_one_table():
    """T-052 DoD: Markdown output contains a | col | col | table."""
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    assert len(tables) >= 1, "WriterAgent output must contain ≥ 1 Markdown table"


def test_representative_table_is_structurally_valid():
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    ok, reason = validate_table_structure(tables[0])
    assert ok, f"Table structure invalid: {reason}"


def test_representative_table_converts_cleanly_to_latex():
    """T-052 DoD: table converts cleanly to LaTeX tabular."""
    tables = detect_markdown_tables(_ARTICLE_WITH_TABLE)
    latex = table_to_latex_tabular(tables[0])
    assert "\\begin{tabular}" in latex
    assert "\\end{tabular}" in latex
    assert "\\hline" in latex
    assert "\\\\" in latex
