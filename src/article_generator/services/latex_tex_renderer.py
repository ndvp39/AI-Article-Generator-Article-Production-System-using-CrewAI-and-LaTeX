from __future__ import annotations

import re

from article_generator.services.latex_doc_builder import apply_inline


def convert_body(markdown: str) -> str:
    """Convert a Markdown article body to LaTeX body text."""
    lines = markdown.splitlines()
    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        formula_match = re.match(r"<!--\s*FORMULA:\s*(.*?)\s*-->", stripped)
        if formula_match:
            output.append(r"\begin{equation}")
            output.append(f"    {formula_match.group(1)}")
            output.append(r"\end{equation}")
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            output.append(table_to_tabularx(table_lines))
            continue

        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            title = apply_inline(m.group(2))
            cmd = {1: r"\section", 2: r"\subsection", 3: r"\subsubsection"}[level]
            output.append(rf"{cmd}{{{title}}}")
            i += 1
            continue

        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if img_match:
            output.append(image_to_figure(img_match.group(2), img_match.group(1)))
            i += 1
            continue

        if not stripped:
            output.append("")
            i += 1
            continue

        output.append(apply_inline(line))
        i += 1

    return "\n".join(output)


def table_to_tabularx(rows: list[str]) -> str:
    """Convert a list of Markdown pipe-table rows to a LaTeX tabularx environment."""
    if len(rows) < 3:
        return ""
    header_cells = parse_row(rows[0])
    n_cols = len(header_cells)
    col_spec = "l" * (n_cols - 1) + "X" if n_cols > 1 else "X"
    header_row = "  " + " & ".join(
        rf"\textbf{{{apply_inline(c)}}}" for c in header_cells
    ) + r" \\"
    data_rows: list[str] = []
    for row in rows[2:]:
        cells = parse_row(row)
        cells = (cells + [""] * n_cols)[:n_cols]
        data_rows.append("  " + " & ".join(apply_inline(c) for c in cells) + r" \\")
    return "\n".join([
        r"\begin{table}[htbp]", r"  \centering",
        rf"  \begin{{tabularx}}{{\textwidth}}{{{col_spec}}}",
        r"  \toprule", header_row, r"  \midrule",
        *data_rows,
        r"  \bottomrule", r"  \end{tabularx}", r"\end{table}",
    ])


def parse_row(row: str) -> list[str]:
    """Split a Markdown table row string into cell strings."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def image_to_figure(path: str, alt: str) -> str:
    """Convert a Markdown image reference to a LaTeX figure environment."""
    latex_path = path.replace("\\", "/")
    label = re.sub(r"[^a-zA-Z0-9]", "_", alt.lower()) or "fig"
    caption = alt or "Figure"
    return "\n".join([
        r"\begin{figure}[htbp]", r"  \centering",
        rf"  \includegraphics[width=0.85\textwidth]{{{latex_path}}}",
        rf"  \caption{{{caption}}}", rf"  \label{{fig:{label}}}",
        r"\end{figure}",
    ])
