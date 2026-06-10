# PRD_bidi.md — Dedicated PRD: Hebrew-English BiDi (Bidirectional Text)
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Bidirectional Text and the Unicode BiDi Algorithm
Natural languages are either **left-to-right (LTR)** — English, French, German — or **right-to-left (RTL)** — Hebrew, Arabic, Farsi. When both appear in the same document, a **BiDi algorithm** (Unicode Standard, Annex #9) determines the display order of characters in each line.

Key concepts:
- **Base direction:** The dominant text direction of the current paragraph or page.
- **Embedding level:** How deeply nested a direction change is (0 = base, 1 = first override, …).
- **Weak characters:** Punctuation, spaces, numbers — resolved by surrounding strong characters.
- **Neutral characters:** Spaces between directional runs — resolved by context.

In mixed Hebrew-English documents, authors typically write **in the primary language** (the language that dominates) and embed the secondary language inline. For this project, the article is primarily in **Hebrew (RTL)** — all prose, headings, and explanations are written in Hebrew. English appears as the secondary, embedded language for technical terms, variable names, code identifiers, and citations, which must be LTR-guarded within Hebrew paragraphs.

### 1.2 LaTeX BiDi Support: bidi and polyglossia
Plain LaTeX's typesetting engine (TeX) has no BiDi support. Two packages are required:

| Package | Role |
|---------|------|
| `bidi` | Core right-to-left typesetting engine; redefines paragraph building to support RTL direction |
| `polyglossia` | Modern multilingual support for LuaLaTeX/XeLaTeX; loads correct hyphenation, fonts, and typography per language |

**Engine requirement:** `bidi` requires either **LuaLaTeX** or **XeLaTeX**. It is **incompatible with pdflatex**. This is why `pdflatex` is forbidden in Project.md §4.

> `polyglossia` supersedes the older `babel` package for XeLaTeX/LuaLaTeX. `babel` also has BiDi support but is less capable with OpenType fonts and modern Unicode.

### 1.3 The `bidi` Package Direction Model
The `bidi` package introduces these LaTeX macros:

| Macro | Effect |
|-------|--------|
| `\setRTL` | Switch entire document to RTL (useful for RTL-primary documents) |
| `\setLTR` | Switch entire document back to LTR |
| `\RLE{text}` | Run of RTL text embedded in an LTR paragraph |
| `\LRE{text}` | Run of LTR text embedded in an RTL paragraph |
| `\begin{RTL}...\end{RTL}` | Block-level RTL environment |
| `\begin{LTR}...\end{LTR}` | Block-level LTR environment |

### 1.4 polyglossia Language Configuration
`polyglossia` configures multiple active languages per document:

```latex
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
```

Switching language context:
```latex
English text here.
\begin{hebrew}
זה טקסט בעברית. הוא נקרא מימין לשמאל.
\end{hebrew}
Back to English.
```

The `hebrew` environment automatically:
- Reverses paragraph direction to RTL
- Loads Hebrew-appropriate hyphenation (no hyphenation — Hebrew doesn't use it)
- Applies the active Hebrew font

### 1.5 Font Requirements for Hebrew
Hebrew requires a font that contains the **Unicode Hebrew block** (U+0590–U+05FF). Standard Latin fonts (Times New Roman, Computer Modern) do not include Hebrew glyphs.

Supported free fonts with Hebrew:
| Font | LaTeX name | Notes |
|------|-----------|-------|
| David CLM | `DavidCLM` | Classic serif Hebrew; CTAN / MiKTeX |
| Frank Rühl CLM | `FrankRuhlCLM` | Default in many Hebrew LaTeX setups |
| Noto Serif Hebrew | `NotoSerifHebrew` | Google Noto family; excellent Unicode |
| Arial / Liberation Sans | `Arial` | System font on Windows; needs `fontspec` |

The project uses `fontspec` (loaded automatically by LuaLaTeX) to specify fonts by name:

```latex
\usepackage{fontspec}
\newfontfamily\hebrewfont[Script=Hebrew]{FrankRuhlCLM}
```

### 1.6 Math in BiDi Documents
Mathematical formulas always render **LTR** regardless of document direction. In RTL paragraphs, displayed equations break the flow:

**Problem:**
```latex
\begin{hebrew}
הנוסחה הבאה מתארת ירידת גרדיאנט:
\[ \theta \leftarrow \theta - \alpha \nabla_\theta \mathcal{L}(\theta) \]
\end{hebrew}
```
This compiles with bidir issues — the formula is LTR but the surrounding text is RTL.

**Fix:** Explicitly wrap the equation in an `\LRE{}` or `equation` environment with direction override:
```latex
\begin{hebrew}
הנוסחה הבאה מתארת ירידת גרדיאנט:
\end{hebrew}
\begin{equation}
\theta \leftarrow \theta - \alpha \nabla_\theta \mathcal{L}(\theta)
\end{equation}
\begin{hebrew}
כאשר \LRE{$\alpha$} הוא קצב הלמידה.
\end{hebrew}
```

### 1.7 Tables and Figures in RTL Context
Tables inside an RTL block have column order reversed by `bidi` by default. To prevent this:
```latex
\begin{LTR}
\begin{table}[h]
  % ... normal LTR table ...
\end{table}
\end{LTR}
```

Figures (images, TikZ) are direction-neutral and do not require special treatment.

---

## 2. Requirements

### 2.1 Functional Requirements

**REQ-BIDI-01: At Least One Hebrew Chapter**
The compiled article MUST contain at least one chapter or major section with substantive Hebrew RTL text. A single word or label is insufficient — minimum 3 consecutive Hebrew sentences.

**REQ-BIDI-02: Correct RTL Paragraph Direction**
All Hebrew text blocks MUST be typeset right-to-left. English words embedded within Hebrew paragraphs MUST remain LTR via `\LRE{}` or automatic Unicode BiDi resolution.

**REQ-BIDI-03: Correct LTR Paragraph Direction**
All English text blocks MUST be typeset left-to-right. Hebrew words embedded within English paragraphs MUST be wrapped in `\RLE{}` or an inline `\texthebrew{}` command.

**REQ-BIDI-04: Hebrew Font Loaded**
The LaTeX preamble MUST configure a Hebrew-capable font using `fontspec` and `polyglossia`. Compilation MUST NOT produce "missing character" warnings for any Hebrew Unicode codepoint used in the document.

**REQ-BIDI-05: Formulas Correct in RTL Context**
Mathematical formulas appearing within or adjacent to Hebrew text MUST compile without BiDi corruption. Inline math in Hebrew paragraphs MUST use `\LRE{$...$}` wrapping. Display math environments (`equation`, `align`) MUST be placed outside `hebrew` environments.

**REQ-BIDI-06: Tables Correct in RTL Context**
Tables appearing within RTL sections MUST be wrapped in a `\begin{LTR}...\end{LTR}` block to preserve column order.

**REQ-BIDI-07: Section Headings BiDi-Correct**
Section headings in Hebrew chapters MUST be RTL-aligned. English section headings MUST be LTR-aligned. `\section{}` calls inside a `hebrew` environment automatically inherit RTL alignment from `polyglossia`.

**REQ-BIDI-08: No Mixed-Direction Artifacts**
The compiled PDF MUST NOT exhibit:
- Reversed punctuation (period appearing at left of RTL sentence)
- Scrambled word order in mixed-direction lines
- Overlapping glyphs from direction resolution failures
- Missing characters (boxes □ where Hebrew glyphs should appear)

**REQ-BIDI-09: Bibliography RTL-Compatible**
Author names containing Hebrew characters (e.g., `ברין, סרגיי`) in `.bib` entries MUST render correctly in the bibliography. `biber` + `biblatex` with UTF-8 encoding handles this natively.

**REQ-BIDI-10: BiDiSpecialistAgent Validation**
The `BiDiSpecialistAgent` MUST scan the LaTeX output for common BiDi failure patterns before compilation and inject fixes. Specifically it checks for:
- Plain Hebrew text outside a `hebrew` environment
- Inline math `$...$` inside a `\begin{hebrew}` without `\LRE{}` wrapping
- Tables inside RTL blocks without `\begin{LTR}` guard

### 2.2 Non-Functional Requirements

**NFR-BIDI-01:** Zero "missing character" warnings in XeLaTeX log for Hebrew Unicode codepoints.  
**NFR-BIDI-02:** Zero reversed-word-order or mirrored-punctuation artifacts visible in compiled PDF.  
**NFR-BIDI-03:** BiDi validation pass by `BiDiSpecialistAgent` MUST complete in ≤ 30 seconds.  
**NFR-BIDI-04:** Hebrew font MUST be available in the MiKTeX installation; `LaTeXCompiler` MUST verify font availability before compilation and raise `FontNotFoundError` if missing.  
**NFR-BIDI-05:** All BiDi-related LaTeX macro usage MUST be encapsulated in `bidi_helpers.py`; no scattered `\RLE`, `\LRE` strings hard-coded in agent prompts.

---

## 3. Architecture

### 3.1 BiDi in the Agent Pipeline

```
ResearcherAgent
    │  (finds Hebrew-language sources if topic warrants)
    ▼
WriterAgent
    │  writes Hebrew article (main language RTL) with English technical terms inline
    │  uses plain Hebrew text (Unicode) in its output
    ▼
EditorAgent
    │  reviews and improves the article; preserves Hebrew content
    ▼
LaTeXFormatterAgent
    │  converts Markdown to .tex with polyglossia preamble
    │  inserts \setmainlanguage{hebrew}, language environments, wraps math
    ▼
BiDiSpecialistAgent          ◄── Final BiDi validation pass
    │  scans LaTeX for bare Hebrew outside language environments
    │  wraps inline math in \LRE{$...$} inside hebrew blocks
    │  wraps tables in \begin{LTR}...\end{LTR} inside RTL blocks
    │  MUST NOT add or inject any new content — only fix existing markup
    ▼
LaTeXCompiler
    │  runs 4-pass xelatex/biber pipeline
    │  checks log for BiDi warnings
    ▼
  article.pdf
```

### 3.2 `bidi_helpers.py` Interface

```python
def wrap_hebrew_block(text: str) -> str:
    """Wrap text in \begin{hebrew}...\end{hebrew}."""

def wrap_lre(math_expr: str) -> str:
    """Wrap inline math in \LRE{$...$} for use inside Hebrew blocks."""

def guard_table_in_rtl(table_latex: str) -> str:
    """Wrap a table environment in \begin{LTR}...\end{LTR}."""

def scan_for_bare_hebrew(latex_content: str) -> list[BidiIssue]:
    """Return list of locations where Hebrew text appears outside hebrew env."""

def scan_for_unguarded_math(latex_content: str) -> list[BidiIssue]:
    """Return list of inline math inside hebrew env without \\LRE wrapping."""

def auto_fix(latex_content: str) -> tuple[str, list[BidiIssue]]:
    """Apply all fixes; return (fixed_content, list of issues that were fixed)."""
```

### 3.3 `BidiIssue` Data Model

```python
@dataclass
class BidiIssue:
    line_number: int
    issue_type: str   # "bare_hebrew" | "unguarded_math" | "rtl_table"
    original:  str    # the offending fragment
    fix:       str    # the replacement applied
    severity:  str    # "error" | "warning"
```

---

## 4. LaTeX Preamble for BiDi

### 4.1 Minimal Correct Preamble

```latex
\documentclass[12pt,a4paper]{article}

% --- ENGINE MUST BE LuaLaTeX or XeLaTeX ---

% Font configuration (fontspec only works with Lua/XeLaTeX)
\usepackage{fontspec}
\setmainfont{Times New Roman}
\newfontfamily\hebrewfont[Script=Hebrew,Scale=1.0]{FrankRuhlCLM}

% Bidirectional and multilingual support
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}

% Must come AFTER polyglossia
\usepackage{bidi}

% ... rest of preamble (hyperref, biblatex, etc.) ...
```

> **Package order is critical:** `bidi` MUST be loaded after `polyglossia`, `fontspec`, and all other packages that redefine paragraph/line-breaking primitives. Loading `bidi` too early causes mysterious compilation failures.

### 4.2 Full Package Loading Order

```latex
\usepackage{fontspec}        % 1. Font selection
\usepackage{polyglossia}     % 2. Language support
\usepackage{geometry}        % 3. Page layout
\usepackage{fancyhdr}        % 4. Headers/footers
\usepackage{graphicx}        % 5. Images
\usepackage{amsmath,amssymb} % 6. Math
\usepackage{booktabs}        % 7. Tables
\usepackage{tabularx}        % 8. Flexible tables
\usepackage{xcolor}          % 9. Colors
\usepackage{tikz}            % 10. TikZ diagrams
\usepackage[backend=biber,style=numeric]{biblatex}  % 11. Bibliography
\usepackage{hyperref}        % 12. Hyperlinks (near-last)
\usepackage{bidi}            % 13. BiDi — MUST BE LAST (or near-last)
```

> **Rule:** `hyperref` before `bidi`; `bidi` last (or second-to-last if `cleveref` used).

---

## 5. Content Contract: Hebrew Chapter

### 5.1 Required Hebrew Content
The `WriterAgent` MUST produce content for a Hebrew chapter matching this template structure:

```
[Chapter heading in Hebrew]
[3+ sentences of substantive Hebrew text explaining a concept]
[At least one embedded English technical term wrapped inline]
[Reference to at least one citation using \cite{key}]
[Optional: one formula with \LRE wrapping]
```

### 5.2 Example Compliant Hebrew Section

```latex
\section{למידת מכונה — סקירה}
\begin{hebrew}
למידת מכונה היא תת-תחום של בינה מלאכותית העוסק בפיתוח אלגוריתמים
שמאפשרים למחשבים ללמוד מנתונים \cite{russell2020ai}.
הגישה המרכזית כיום היא \LRE{deep learning},
המתבססת על רשתות נוירונים בעלות מספר רב של שכבות \cite{lecun2015deep}.

נוסחת עדכון המשקלות ב-\LRE{gradient descent} היא:
\end{hebrew}
\begin{equation}
  \theta_{t+1} = \theta_t - \alpha \nabla_\theta \mathcal{L}(\theta_t)
\end{equation}
\begin{hebrew}
כאשר \LRE{$\alpha$} הוא קצב הלמידה ו-\LRE{$\mathcal{L}$} היא פונקציית ההפסד.
\end{hebrew}
```

### 5.3 `BiDiSpecialistAgent` Task Contract

| Field | Value |
|-------|-------|
| **Input** | Raw LaTeX content string from `LaTeXFormatterAgent` |
| **Output** | BiDi-corrected LaTeX string + list of `BidiIssue` objects |
| **Raises** | `BidiValidationError` if unfixable issues remain after auto-fix |
| **Side effects** | Logs all issues to `CompilationResult.bidi_issues` |

---

## 6. Input / Output Contract

### 6.1 `BiDiSpecialistAgent.run(latex_content: str) → BiDiResult`

| Field | Detail |
|-------|--------|
| **Input** | `latex_content: str` — full `.tex` document content |
| **Output** | `BiDiResult` — corrected content + issue list |
| **Raises** | `BidiValidationError` if `severity=="error"` issues remain |

```python
@dataclass
class BiDiResult:
    corrected_latex: str
    issues_found:    list[BidiIssue]
    issues_fixed:    list[BidiIssue]
    issues_unfixed:  list[BidiIssue]   # must be empty for success
    hebrew_env_count: int              # number of \begin{hebrew} blocks
    validation_passed: bool
```

### 6.2 Success Condition
`BiDiResult.validation_passed == True` requires:
1. `len(issues_unfixed) == 0`
2. `hebrew_env_count >= 1` (at least one Hebrew block present)
3. Zero "missing character" warnings in subsequent XeLaTeX log

---

## 7. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Hebrew env count | ≥ 1 | `BiDiResult.hebrew_env_count` |
| Unguarded math in RTL | 0 | `BidiIssue` count with `type="unguarded_math"` |
| Bare Hebrew outside env | 0 | `BidiIssue` count with `type="bare_hebrew"` |
| Missing character warnings | 0 | Count of `Missing character:` in XeLaTeX log |
| BiDi agent runtime | ≤ 30 s | Wall clock of `BiDiSpecialistAgent.run()` |
| RTL table artifacts | 0 | `BidiIssue` count with `type="rtl_table"` |
| Punctuation direction errors | 0 | Manual PDF review |

---

## 8. Constraints

1. **XeLaTeX required:** `pdflatex` cannot compile `bidi` + `polyglossia`. Any attempt to use `pdflatex` MUST raise `EngineNotSupportedError`. XeLaTeX is the primary engine; LuaLaTeX is an acceptable alternative.
2. **Package order enforced:** `bidi` MUST be the last (or second-to-last) package loaded. `LaTeXFormatterAgent` MUST NOT allow `bidi` to appear before `polyglossia` in the preamble.
3. **No babel:** `babel` MUST NOT be used in the same document as `polyglossia`. They conflict.
4. **Hebrew font required:** If the Hebrew font is not found by `fontspec`, `LaTeXCompiler` MUST raise `FontNotFoundError` with instructions for installing the missing font via MiKTeX Package Manager.
5. **Language consistency:** The `BiDiSpecialistAgent` MUST NOT inject `\begin{hebrew}` blocks or any language-switching content. Language structure is set by the `LaTeXFormatterAgent`. The bidi agent only fixes structural markup issues in the existing content.
6. **No plain Unicode Hebrew outside environments:** Raw Hebrew characters (U+0590–U+05FF) outside a `hebrew` environment or `\RLE{}` command MUST be flagged as errors, not warnings, and fixed before compilation.

---

## 9. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **babel + pdflatex** | `pdflatex` cannot handle Unicode Hebrew without complex escaping. `babel` is less capable than `polyglossia` for OpenType fonts. Both rejected by Project.md §4. |
| **LuaTeX bidi (native)** | LuaTeX 0.95+ has experimental native BiDi support without `bidi` package. Unstable; not yet production-ready as of MiKTeX 2024. `bidi` package is the mature, documented solution. |
| **Manual `\hbox{} + \rlap{}`** | Possible for simple cases but does not handle full paragraph RTL; no Hebrew hyphenation; breaks with `hyperref`. Too fragile for a 15-page article. |
| **Separate Hebrew document + merge** | Generating RTL and LTR content as separate PDFs and merging with `pdfpages` avoids BiDi entirely but produces no mixed-direction pages — violates Project.md §3 requirement. |
| **Arabic font package (`arabtex`)** | Designed for Arabic, not Hebrew. Different Unicode block, different rendering engine. Not applicable. |
| **LuaLaTeX instead of XeLaTeX** | LuaLaTeX also supports `bidi` + `polyglossia`. XeLaTeX is preferred because it has more stable `bidi` package compatibility in current MiKTeX versions. |

---

## 10. Success Criteria

The BiDi system is considered successful when all of the following are true:

- [ ] Article contains ≥ 1 substantive Hebrew chapter/section (≥ 3 Hebrew sentences).
- [ ] All Hebrew text renders RTL in the compiled PDF — no scrambled word order.
- [ ] All English text within Hebrew sections renders LTR (wrapped in `\LRE{}`).
- [ ] Zero "missing character" warnings in XeLaTeX log for Hebrew glyphs.
- [ ] Mathematical formulas in/near Hebrew sections compile without BiDi corruption.
- [ ] Tables in RTL sections preserve correct LTR column order via `\begin{LTR}` guard.
- [ ] `BiDiSpecialistAgent` detects and fixes all `bare_hebrew` and `unguarded_math` issues before LaTeX compilation.
- [ ] `BiDiResult.validation_passed == True` for full article.
- [ ] `biber` processes Hebrew author names in `.bib` without errors or warnings.
- [ ] Compiled PDF is visually inspected: punctuation at correct end, no glyph overlap, correct reading direction.

---

## 11. Test Scenarios

### Scenario T-001: Hebrew block renders RTL
**Setup:** `.tex` file with `\begin{hebrew}שלום עולם\end{hebrew}`  
**Action:** Compile with LuaLaTeX  
**Expected:** "שלום עולם" renders right-to-left in PDF; no missing character warnings

### Scenario T-002: Inline math in Hebrew guarded
**Setup:** `\begin{hebrew}...\$x = 5\$...\end{hebrew}` (unguarded)  
**Action:** `BiDiSpecialistAgent.run()` called  
**Expected:** `BidiIssue(type="unguarded_math")` detected; auto-fixed to `\LRE{$x = 5$}`; `issues_fixed` has 1 entry

### Scenario T-003: Bare Hebrew outside environment detected
**Setup:** `.tex` with raw `שלום` text outside any `hebrew` environment  
**Action:** `scan_for_bare_hebrew()` called  
**Expected:** Returns `BidiIssue(type="bare_hebrew", severity="error")` at correct line number

### Scenario T-004: Table in RTL guarded
**Setup:** `\begin{hebrew}` block containing a `tabular` environment  
**Action:** `auto_fix()` called  
**Expected:** `tabular` wrapped in `\begin{LTR}...\end{LTR}`; `BidiIssue(type="rtl_table")` logged

### Scenario T-005: Package order enforced
**Setup:** `.tex` preamble with `bidi` loaded before `polyglossia`  
**Action:** `LaTeXFormatterAgent` validates preamble  
**Expected:** `PackageOrderError` raised with message specifying correct order; compilation not attempted

### Scenario T-006: Missing Hebrew font
**Setup:** System without FrankRuhlCLM installed; article has Hebrew content  
**Action:** `LaTeXCompiler.compile()` called  
**Expected:** `FontNotFoundError` raised with message: "Hebrew font 'FrankRuhlCLM' not found. Install via MiKTeX Package Manager: mpm --install frankruhlclm"

### Scenario T-007: English-only article — no content injected
**Setup:** `.tex` file with zero `\begin{hebrew}` environments (article written in English)  
**Action:** `BiDiSpecialistAgent.run()` called  
**Expected:** `BiDiScanner` returns `[]`; agent writes unchanged file and reports 0 issues found. No Hebrew content added.

### Scenario T-008: Hebrew citation renders correctly
**Setup:** `.bib` entry with `author = "ברין, סרגיי and Page, Lawrence"`; cited in Hebrew section  
**Action:** Full 4-pass compilation  
**Expected:** Bibliography entry shows Hebrew author name correctly; no biber warnings for the entry; citation link is clickable

### Scenario T-009: Mixed Hebrew-English paragraph
**Setup:** Hebrew paragraph with inline English term: `\begin{hebrew}אלגוריתם \LRE{backpropagation} משמש...\end{hebrew}`  
**Action:** Compile with LuaLaTeX; inspect PDF  
**Expected:** "backpropagation" renders LTR inside the RTL paragraph; text flows correctly; no glyph overlap
