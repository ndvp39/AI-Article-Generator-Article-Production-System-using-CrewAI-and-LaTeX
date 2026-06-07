# PRD_latex_pipeline.md — Dedicated PRD: LaTeX Generation & Compilation Pipeline
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 LaTeX as a Typesetting System
LaTeX is a document preparation system built on top of Donald Knuth's TeX engine. Unlike word processors, LaTeX separates content from presentation: the author writes structural markup (`.tex` source files) and a compiler transforms it into a precisely typeset PDF. LaTeX is the de-facto standard for academic and scientific publishing because it handles:

- Mathematical typesetting (AMS packages) with correct spacing and notation
- Automatic cross-referencing, numbering, and hyperlinking
- Professional bibliography management (BibTeX/biber)
- Complex multi-column, multi-language, multi-directional layouts
- Consistent typographic quality regardless of document length

### 1.2 Compilation Engines
Three main engines compile `.tex` → PDF:

| Engine | Unicode | OpenType Fonts | BiDi (Hebrew) | Speed |
|--------|---------|----------------|---------------|-------|
| `pdflatex` | Limited | No | Not natively | Fast |
| `xelatex` | Full | Yes | Yes (bidi pkg) | Medium |
| `lualatex` | Full | Yes | Yes (luabidi) | Slower |

**Choice:** `lualatex` as primary, `xelatex` as fallback — both are mandated by Project.md §4 and support the Hebrew–English BiDi requirement. `pdflatex` is explicitly excluded.

### 1.3 Multi-Pass Compilation
LaTeX resolves cross-references (TOC entries, citations, figure numbers, hyperlinks) in a deferred manner — they are written to auxiliary files (`.aux`, `.toc`, `.bbl`) during one pass and read back on the next. This is why **multiple compilation passes are required**:

| Pass | Command | Purpose |
|------|---------|---------|
| Pass 1 | `lualatex article.tex` | First parse; writes `.aux` with undefined references |
| Pass 2 | `biber article` | Reads `.aux`, generates `.bbl` bibliography file |
| Pass 3 | `lualatex article.tex` | Reads `.bbl`; resolves citations; writes updated `.aux` |
| Pass 4 | `lualatex article.tex` | Resolves any remaining cross-refs (TOC, hyperlinks) |

**Warning from Project.md §4:** *"If clicking a reference in the document does not jump to the citation in the bibliography — it means a compilation is missing."* Therefore exactly 4 passes are mandatory.

### 1.4 Bibliography Management
BibTeX and its modern successor **biber** process `.bib` files — structured databases of references — and produce formatted bibliography sections. The workflow:

1. References stored in `references.bib` with BibTeX entries (`@article`, `@book`, `@inproceedings`, etc.)
2. In-text citations use `\cite{key}` commands
3. `biber` reads the `.aux` file, matches keys, formats entries per the citation style, writes `.bbl`
4. Final LaTeX pass reads `.bbl` and renders the bibliography section

### 1.5 Hebrew–English BiDi in LaTeX
Hebrew is written right-to-left (RTL); English is written left-to-right (LTR). Standard LaTeX assumes LTR only. BiDi support requires:

- **`polyglossia`** package (recommended with LuaLaTeX) — supports multilingual documents with proper font and direction switching
- **`bidi`** package — low-level RTL/LTR direction primitives: `\LR{}`, `\RL{}`, `\LRE{}`, `\RLE{}`
- **Hebrew font** — e.g., `David CLM`, `Frank Rühl CLM`, or `Noto Serif Hebrew` (OpenType, required by LuaLaTeX/XeLaTeX)

Direction switching in the document body uses `\begin{RTL}...\end{RTL}` or `\begin{LTR}...\end{LTR}` for block-level switching.

### 1.6 TikZ for Block Diagrams
**TikZ** (TikZ ist kein Zeichenprogramm) is the standard LaTeX package for creating vector graphics, flow charts, and block diagrams programmatically within the `.tex` source. It is explicitly recommended in Project.md §4 for schematics. TikZ figures do not require external files — they compile directly from the `.tex` source.

---

## 2. Requirements

### 2.1 Mandatory Document Structure
The generated `.tex` file MUST produce a PDF with ALL of the following structural elements:

| Element | LaTeX Implementation | Mandatory |
|---------|---------------------|-----------|
| Cover / Title page | `\maketitle` or custom title block | YES |
| Table of Contents | `\tableofcontents` | YES |
| Chapter / Section divisions | `\chapter{}` or `\section{}` | YES |
| Headers | `\fancyhead` via `fancyhdr` | YES |
| Footers with page numbers | `\fancyfoot` + `\thepage` | YES |
| At least one image | `\includegraphics` | YES |
| At least one Python-generated graph | `\includegraphics` (from `assets/`) | YES |
| At least one table within margins | `tabular` / `tabularx` / `booktabs` | YES |
| At least one "fancy" math formula | `equation` / `align` env. | YES |
| BiDi chapter (RTL/LTR) | `polyglossia` + direction macros | YES |
| Bibliography section | `\bibliography{references}` | YES |
| Clickable hyperlinks throughout | `hyperref` package | YES |

### 2.2 Mandatory Preamble Packages

```latex
\documentclass[12pt,a4paper]{article}   % or {report} / {book}

% Engine & language
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
\newfontfamily\hebrewfont[Script=Hebrew]{David CLM}

% Layout & structure
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{hyperref}
\usepackage{setspace}

% Mathematics
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{mathtools}

% Figures & tables
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{float}

% Graphics / diagrams
\usepackage{tikz}

% Bibliography
\usepackage[backend=biber, style=numeric, sorting=nyt]{biblatex}
\addbibresource{references.bib}
```

### 2.3 Cover Sheet Requirements
The title page MUST display all five fields from `config/setup.json`:

```latex
\title{\textbf{<topic>}}
\author{<author>}
\date{<date>}
% Custom fields via \maketitle override or titlepage environment:
% Course: <course>
% Lecturer: <lecturer>
```

### 2.4 Mathematical Formula Requirements
- MUST use at least one LaTeX math environment: `equation`, `equation*`, `align`, `align*`, `gather`, or `multline`
- Formula MUST contain at least one of: `\frac{}{}`, `\sum_{}^{}`, `\int_{}^{}`, `\nabla`, `\partial`, matrix environment, or subscript/superscript notation
- Plain-text representations (e.g., `f(x) = sigma(wx + b)`) are strictly forbidden
- Example of acceptable "fancy formula":

```latex
\begin{equation}
    \nabla_\theta \mathcal{L}(\theta) = \frac{1}{N} \sum_{i=1}^{N}
    \left[ \hat{y}_i - y_i \right] \cdot \frac{\partial \hat{y}_i}{\partial \theta}
\end{equation}
```

### 2.5 Table Requirements
- MUST use `booktabs` (`\toprule`, `\midrule`, `\bottomrule`) for professional formatting
- MUST fit within page margins — use `tabularx` with `\textwidth` or `\resizebox{\textwidth}{!}{...}` for wide tables
- MUST NOT overflow horizontally; LaTeX `Overfull \hbox` warnings for tables are treated as errors

### 2.6 Image & Graph Requirements
- Images from `assets/` using `\includegraphics[width=\linewidth]{assets/filename}`
- Python-generated graph from `assets/article_graph.png` (produced by `GraphRunner`)
- All figures MUST have a `\caption{}` and `\label{}`
- All figures MUST be referenced in-text with `\ref{fig:label}`

---

## 3. Compilation Pipeline Specification

### 3.1 Pipeline Steps
```
Input: article.tex + references.bib + assets/
  │
  ├── Pass 1: lualatex --interaction=nonstopmode article.tex
  │   Output: article.aux, article.toc (undefined refs)
  │
  ├── Pass 2: biber article
  │   Output: article.bbl (bibliography)
  │
  ├── Pass 3: lualatex --interaction=nonstopmode article.tex
  │   Output: article.aux updated (citations resolved)
  │
  └── Pass 4: lualatex --interaction=nonstopmode article.tex
      Output: article.pdf (all cross-refs resolved)
```

### 3.2 Subprocess Interface
Each compilation pass is invoked as a subprocess:

```python
result = subprocess.run(
    ["lualatex", "--interaction=nonstopmode", tex_filename],
    cwd=output_dir,
    capture_output=True,
    text=True,
    timeout=300,       # seconds per pass
)
```

### 3.3 Error Detection
LaTeX does not return non-zero exit code for all errors. The system MUST check BOTH:
1. `result.returncode != 0` — subprocess failure
2. Scan `article.log` for lines beginning with `!` (LaTeX fatal errors)

Log scanning pattern:
```python
errors = [line for line in log_content.splitlines() if line.startswith("!")]
```

### 3.4 Warning Detection (non-fatal but tracked)
The system SHOULD detect and log these warnings from the `.log` file:
- `Overfull \hbox` — table or content overflowing margins
- `Citation ... undefined` — missing `.bib` entry
- `Reference ... undefined` — missing `\label`
- `Package hyperref Warning` — hyperlink issues

---

## 4. Input / Output Contract

### 4.1 `LaTeXCompiler.generate_tex()` — Markdown to .tex

| Field | Detail |
|-------|--------|
| **Input** | `markdown: str` — complete reviewed Markdown article |
| **Input** | `config: ArticleConfig` — topic, author, date, course, lecturer, paths |
| **Output** | `str` — complete `.tex` file content |
| **Side effects** | Writes `.tex` to `config.paths.output_dir` |
| **Raises** | `LaTeXGenerationError` if required sections missing from Markdown |

**Conversion rules:**
| Markdown | LaTeX |
|----------|-------|
| `# Heading` | `\section{Heading}` |
| `## Heading` | `\subsection{Heading}` |
| `**bold**` | `\textbf{bold}` |
| `*italic*` | `\textit{italic}` |
| `` `code` `` | `\texttt{code}` |
| `\| table \|` | `tabularx` environment |
| `<!-- FORMULA: ... -->` | `equation` environment |
| `![img](path)` | `\includegraphics{path}` |
| `[text](url)` | `\href{url}{text}` |
| `[@cite_key]` | `\cite{cite_key}` |

### 4.2 `LaTeXCompiler.generate_bib()` — References to .bib

| Field | Detail |
|-------|--------|
| **Input** | `references: list[Reference]` — list of reference objects from Researcher output |
| **Output** | `str` — valid `.bib` file content |
| **Side effects** | Writes `.bib` to `config.paths.output_dir` |
| **Raises** | `BibGenerationError` if reference missing required fields |

**Minimum BibTeX entry fields per type:**
| Type | Required fields |
|------|----------------|
| `@article` | `author`, `title`, `journal`, `year`, `volume` |
| `@book` | `author`, `title`, `publisher`, `year` |
| `@inproceedings` | `author`, `title`, `booktitle`, `year` |
| `@misc` | `author`, `title`, `year`, `url` |

### 4.3 `LaTeXCompiler.compile()` — 4-pass Compilation

| Field | Detail |
|-------|--------|
| **Input** | `tex_path: str` — absolute path to `.tex` file |
| **Input** | `bib_path: str` — absolute path to `.bib` file |
| **Output** | `CompilationResult` — success, passes completed, pdf_path, errors, warnings, log_path |
| **Side effects** | Writes `article.pdf`, `article.log`, `article.aux`, `article.bbl` to `results/` |
| **Raises** | `CompilationError` if any pass produces fatal LaTeX errors |

---

## 5. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Compilation time (4 passes) | ≤ 5 minutes | Wall clock from first lualatex to PDF |
| PDF page count | ≥ 15 pages | `pdfinfo article.pdf \| grep Pages` |
| LaTeX fatal errors | 0 | Lines starting with `!` in `.log` |
| `Overfull \hbox` warnings for tables | 0 | Log scan |
| Undefined citations | 0 | Log scan for `Citation ... undefined` |
| Undefined references | 0 | Log scan for `Reference ... undefined` |
| All hyperlinks functional | 100% | Manual PDF test |

---

## 6. Constraints

1. **Engine:** LuaLaTeX MUST be used as the primary engine. XeLaTeX is the only permitted fallback. `pdflatex` is forbidden.
2. **Passes:** Exactly 4 passes MUST be executed (1× lualatex, 1× biber, 2× lualatex). Skipping passes will result in broken cross-references.
3. **Error handling:** The system MUST NOT silently ignore LaTeX fatal errors. `!`-prefixed log lines MUST raise `CompilationError`.
4. **Table overflow:** Any `Overfull \hbox` warning in a `tabular` context MUST be resolved before the pipeline is considered successful.
5. **Formulas:** The LaTeX formatter MUST NOT produce any formula as plain text. Every mathematical expression MUST be inside a LaTeX math environment.
6. **File isolation:** The LaTeX compiler operates in `results/` directory only. It MUST NOT write to `src/`, `config/`, or `docs/`.
7. **Subprocess timeout:** Each individual compilation pass has a 300-second timeout. Timeout raises `CompilationTimeoutError`.

---

## 7. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **pdflatex engine** | Does not support Unicode natively; no OpenType font support; Hebrew BiDi not supported without complex workarounds. Explicitly excluded by Project.md. |
| **Pandoc for Markdown → LaTeX conversion** | Pandoc produces reasonable LaTeX but cannot produce the highly customized preamble (BiDi, custom fancyhdr, specific bibliography style) required. Agent-generated LaTeX gives full control. |
| **WeasyPrint (HTML → PDF)** | No LaTeX math support; produces PDF from HTML/CSS. Cannot reproduce professional academic typesetting quality. |
| **Typst** | Modern alternative to LaTeX; excellent BiDi support; but not specified in Project.md and not standard in academic workflows. |
| **1-pass compilation** | Produces undefined references in TOC and bibliography. Project.md explicitly warns this is insufficient. |
| **2-pass compilation** | Citations resolve but TOC page numbers and hyperlinks may still be undefined. 4 passes are the safe minimum per Project.md. |

---

## 8. Success Criteria

The LaTeX pipeline is considered successful when all of the following are true:

- [ ] `generate_tex()` produces a `.tex` file that LuaLaTeX can parse without fatal errors.
- [ ] Generated `.tex` includes all mandatory preamble packages (polyglossia, fancyhdr, hyperref, amsmath, graphicx, booktabs, biblatex).
- [ ] Cover page displays: topic, author, date, course name, lecturer name.
- [ ] `\tableofcontents` is present and all TOC entries are clickable hyperlinks.
- [ ] Headers show chapter/section title; footers show page number.
- [ ] At least one `equation` or `align` environment with a formula using `\frac`, `\sum`, `\int`, or equivalent.
- [ ] At least one `tabularx` or `tabular` table that does not produce `Overfull \hbox`.
- [ ] At least one `\includegraphics` pointing to a valid file in `assets/`.
- [ ] Compiled PDF has ≥ 15 pages.
- [ ] Zero `!`-prefixed lines in the LaTeX log.
- [ ] Zero `Citation ... undefined` warnings.
- [ ] `CompilationResult.success == True`.
- [ ] `article.pdf` saved to `results/`.

---

## 9. Test Scenarios

### Scenario T-001: Minimal compilable .tex round-trip
**Setup:** Generate a minimal `.tex` with only title, one section, and one `\cite{}`  
**Action:** Run `compile()` with matching minimal `.bib`  
**Expected:** `CompilationResult(success=True, passes_completed=4, errors=[])`; `article.pdf` exists

### Scenario T-002: Fatal LaTeX error is caught
**Setup:** Inject a `.tex` with an undefined command `\undefinedcommand{}`  
**Action:** Run `compile()`  
**Expected:** `CompilationError` raised; `result.errors` contains the `!`-prefixed log line

### Scenario T-003: Table overflow detection
**Setup:** Generate a `.tex` with a wide table that does not use `tabularx`  
**Action:** Run `compile()`, inspect `result.warnings`  
**Expected:** `result.warnings` contains an `Overfull \hbox` entry for the table

### Scenario T-004: Undefined citation detected
**Setup:** Generate `.tex` with `\cite{nonexistent_key}` and a `.bib` without that key  
**Action:** Run `compile()`  
**Expected:** `result.warnings` contains `Citation 'nonexistent_key' undefined`

### Scenario T-005: BiDi preamble present
**Setup:** Run `generate_tex()` with any Markdown input  
**Action:** Inspect generated `.tex` string  
**Expected:** Contains `\usepackage{polyglossia}`, `\setmainlanguage{hebrew}`, `\setotherlanguage{english}`

### Scenario T-006: Fancy formula present in output
**Setup:** Inject Markdown with `<!-- FORMULA: \nabla_\theta \mathcal{L}(\theta) = \sum_i ... -->`  
**Action:** Run `generate_tex()`  
**Expected:** Output `.tex` contains an `equation` or `align` environment with `\nabla`, `\sum`, or equivalent LaTeX math commands; no plain-text fallback

### Scenario T-007: PDF reaches minimum page count
**Setup:** Run full pipeline with realistic article Markdown (~15 pages worth of content)  
**Action:** Run `compile()`; check PDF page count  
**Expected:** `pdfinfo article.pdf` reports `Pages: 15` or more

### Scenario T-008: Subprocess timeout is enforced
**Setup:** Mock `subprocess.run` to hang indefinitely  
**Action:** Call `_run_pass()` with `timeout=1`  
**Expected:** `CompilationTimeoutError` raised within ~1 second
