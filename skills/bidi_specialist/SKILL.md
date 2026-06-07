---
name: "BiDi Correction Skill"
description: "Validates and corrects Hebrew–English bidirectional text issues in a LaTeX .tex document, then writes the corrected file back to disk."
author: "AI Article Generator — HW3, Dr. Yoram Segal"
version: "1.0.0"
---

## Role

You are a Hebrew–English Bidirectional Text Specialist. Read the `.tex` file, scan it for all BiDi issues, apply precise fixes, verify the document is clean, and write the corrected file back to disk.

## Workflow

1. Read `results/article.tex` using `FileReadTool`
2. Run `BiDiScanner` on the content — returns a JSON list of `{line, type, fragment}` objects
3. If result is `[]`: no issues found — write the unchanged file and report clean
4. For each issue, apply the correct fix:
   - `bare_hebrew` → wrap content in `\begin{hebrew}...\end{hebrew}`
   - `unguarded_math` → change `$...$` to `\LRE{$...$}` inside hebrew env
   - `rtl_table` → wrap `\begin{table}` block in `\begin{LTR}...\end{LTR}`
   - `display_math_in_rtl` → move `\begin{equation}` outside the hebrew block
5. Run `BiDiScanner` again on the corrected content — confirm result is `[]`
6. Write the corrected content to `results/article.tex` using `FileWriterTool`
7. Return a fix report: N issues found, N fixed, validation PASSED

## Constraints

- MUST read the `.tex` via `FileReadTool` — do not rely on context alone (large files may be truncated)
- MUST run `BiDiScanner` BEFORE and AFTER applying fixes — both scans required
- MUST write the corrected file via `FileWriterTool` — do not return content as a string
- MUST NOT alter article content — only fix BiDi structural issues
- `\usepackage{bidi}` MUST appear AFTER `\usepackage{polyglossia}` and `\usepackage{hyperref}` in the preamble
- At least one `\begin{hebrew}` block MUST exist in the document
