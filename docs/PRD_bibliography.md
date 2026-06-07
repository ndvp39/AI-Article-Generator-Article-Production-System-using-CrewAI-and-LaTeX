# PRD_bibliography.md — Dedicated PRD: Bibliography Management System
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Academic Bibliography Standards
A bibliography is a structured list of all sources cited within an academic document. It serves two purposes:
1. **Attribution** — crediting original authors and ideas
2. **Verifiability** — allowing readers to locate and verify sources

In academic writing, every factual claim, statistic, or idea drawn from an external source MUST be accompanied by an in-text citation that links to a full bibliographic entry at the document's end.

### 1.2 BibTeX and biber
**BibTeX** (1985, Oren Patashnik) is the original bibliography management system for LaTeX. References are stored in `.bib` files as structured key-value records. The `bibtex` program reads `.aux` files produced by LaTeX, looks up cited keys in `.bib` files, formats entries, and writes `.bbl` files that LaTeX incorporates into the document.

**biber** is the modern successor to BibTeX:
- Full Unicode support (essential for Hebrew author names and non-ASCII titles)
- Works with the `biblatex` package
- More flexible sorting and formatting
- Better handling of multilingual bibliographies

**Choice for this project:** `biber` with `biblatex` — mandatory for Hebrew/Unicode support per Project.md §4.

### 1.3 BibTeX Entry Types and Required Fields

| Entry Type | Used For | Required Fields |
|-----------|---------|----------------|
| `@article` | Journal papers | `author`, `title`, `journal`, `year`, `volume` |
| `@book` | Books | `author`, `title`, `publisher`, `year` |
| `@inproceedings` | Conference papers | `author`, `title`, `booktitle`, `year` |
| `@techreport` | Technical reports | `author`, `title`, `institution`, `year` |
| `@misc` | Websites, software, other | `author`, `title`, `year`, `url`, `note` |
| `@phdthesis` | PhD dissertations | `author`, `title`, `school`, `year` |

### 1.4 biblatex Citation Commands
The `biblatex` package provides rich citation commands:

| Command | Output Example | Use Case |
|---------|---------------|----------|
| `\cite{key}` | [1] | Basic numeric citation |
| `\cite[p.~42]{key}` | [1, p. 42] | Citation with page number |
| `\textcite{key}` | Author [1] | Author name inline |
| `\parencite{key}` | (Author, 2024) | Author-year style |
| `\footcite{key}` | footnote ¹ | Footnote citation |

All citations in this project use `\cite{key}` (numeric style) with `\printbibliography` at the document end.

### 1.5 Citation Keys and Linking
Each `.bib` entry has a unique **citation key** (e.g., `lecun2015deep`). The `hyperref` + `biblatex` combination makes every `\cite{key}` in the document a clickable hyperlink that jumps to the corresponding entry in the bibliography section. This is one of the explicit evaluation criteria in Project.md §5.

### 1.6 .bib File Format
```bibtex
@article{lecun2015deep,
  author    = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  title     = {Deep learning},
  journal   = {Nature},
  year      = {2015},
  volume    = {521},
  number    = {7553},
  pages     = {436--444},
  doi       = {10.1038/nature14539},
  url       = {https://doi.org/10.1038/nature14539}
}

@book{russell2020ai,
  author    = {Russell, Stuart and Norvig, Peter},
  title     = {Artificial Intelligence: A Modern Approach},
  edition   = {4th},
  publisher = {Pearson},
  year      = {2020},
  isbn      = {978-0134610993}
}
```

---

## 2. Requirements

### 2.1 Functional Requirements

**REQ-BIB-01: Minimum Reference Count**
The system MUST produce a `.bib` file containing ≥ 5 bibliography entries. References are gathered by the Researcher agent via `SerperDevTool` and structured by the Writer agent.

**REQ-BIB-02: Entry Completeness**
Every `.bib` entry MUST include at minimum:
- `author` — one or more author names in `Last, First` format
- `title` — full title of the work
- `year` — publication year (4-digit integer)
- At least one of: `journal`, `booktitle`, `publisher`, `url` (type-dependent)

Incomplete entries that cause `biber` warnings are treated as failures.

**REQ-BIB-03: Unique Citation Keys**
Every entry MUST have a globally unique citation key. Keys MUST follow the format: `<firstauthorlastname><year><firstword>` (e.g., `vaswani2017attention`). Duplicate keys cause compilation failure.

**REQ-BIB-04: In-Text Citation Linking**
Every bibliography entry MUST be cited at least once in the article body using `\cite{key}`. Orphaned `.bib` entries (present but never cited) produce `biber` warnings and are treated as poor quality.

**REQ-BIB-05: Clickable Hyperlinks**
With `biblatex` + `hyperref`, every `\cite{key}` command in the compiled PDF MUST be a clickable link that jumps to the bibliography entry. This is an explicit Project.md §5 evaluation criterion.

**REQ-BIB-06: Bibliography as Final Section**
`\printbibliography` MUST appear as the last section of the document, after all content chapters.

**REQ-BIB-07: Bibliography Style**
The system uses numeric citation style (`style=numeric`, `sorting=nyt`) via `biblatex`. Style is configurable from `config/setup.json`.

**REQ-BIB-08: .bib File Generation**
`LaTeXCompiler.generate_bib()` MUST programmatically generate the `.bib` file from structured `Reference` objects produced by the Researcher agent. Manual `.bib` file editing is not part of the workflow.

**REQ-BIB-09: Unicode Support**
Author names and titles containing non-ASCII characters (Hebrew, accented Latin) MUST be stored as-is in UTF-8. `biber` handles Unicode natively; no `{\'{e}}` escaping is needed.

### 2.2 Non-Functional Requirements

**NFR-BIB-01:** `.bib` file MUST be valid BibTeX syntax — parseable by `biber` without errors.  
**NFR-BIB-02:** Bibliography generation MUST complete within 1 second.  
**NFR-BIB-03:** Zero `biber` warnings in the final compilation log.  
**NFR-BIB-04:** `.bib` file saved to `results/references.bib` alongside `article.tex`.

---

## 3. Reference Data Model

### 3.1 `Reference` Object (input to `generate_bib()`)

```python
@dataclass
class Reference:
    key: str              # Unique citation key e.g. "vaswani2017attention"
    entry_type: str       # "article" | "book" | "inproceedings" | "misc"
    author: str           # "Last, First and Last2, First2"
    title: str
    year: int
    journal: str = ""     # for @article
    booktitle: str = ""   # for @inproceedings
    publisher: str = ""   # for @book
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    note: str = ""
```

### 3.2 `Reference` Validation Rules

```python
def validate(ref: Reference) -> None:
    assert ref.key,    "Citation key required"
    assert ref.author, "Author required"
    assert ref.title,  "Title required"
    assert ref.year > 1000, "Valid year required"
    if ref.entry_type == "article":
        assert ref.journal, "@article requires journal"
    if ref.entry_type == "book":
        assert ref.publisher, "@book requires publisher"
    if ref.entry_type == "inproceedings":
        assert ref.booktitle, "@inproceedings requires booktitle"
```

---

## 4. Input / Output Contract

### 4.1 `LaTeXCompiler.generate_bib(references: list[Reference]) → str`

| Field | Detail |
|-------|--------|
| **Input** | `references: list[Reference]` — ≥ 5 validated Reference objects |
| **Output** | `str` — valid `.bib` file content (UTF-8) |
| **Side effects** | Writes to `results/references.bib` |
| **Raises** | `BibGenerationError` if any Reference fails validation |
| **Raises** | `BibGenerationError` if duplicate citation keys detected |

**Generation logic:**
```python
def generate_bib(self, references: list[Reference]) -> str:
    self._validate_references(references)
    self._check_duplicate_keys(references)
    entries = [self._format_entry(ref) for ref in references]
    content = "\n\n".join(entries)
    self._write_file(content, "references.bib")
    return content
```

**Example output for one entry:**
```
@article{vaswani2017attention,
  author    = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and others},
  title     = {Attention Is All You Need},
  journal   = {Advances in Neural Information Processing Systems},
  year      = {2017},
  volume    = {30},
  url       = {https://arxiv.org/abs/1706.03762}
}
```

### 4.2 biblatex Preamble Configuration

```latex
\usepackage[
  backend=biber,
  style=numeric,
  sorting=nyt,
  hyperref=true,
  backref=true
]{biblatex}
\addbibresource{references.bib}
```

| Option | Value | Reason |
|--------|-------|--------|
| `backend=biber` | biber | Unicode support for Hebrew/accented names |
| `style=numeric` | numeric | Standard academic format: [1], [2], ... |
| `sorting=nyt` | name-year-title | Alphabetical sort in bibliography |
| `hyperref=true` | true | Makes citations clickable links |
| `backref=true` | true | Bibliography entries show which pages cite them |

### 4.3 Bibliography Section in .tex

```latex
% At the very end of the document, before \end{document}
\newpage
\printbibliography[title={ביבליוגרפיה / Bibliography}]
```

---

## 5. Compilation Integration

The bibliography pipeline integrates with the 4-pass compilation in `LaTeXCompiler.compile()`:

```
Pass 1: lualatex article.tex
  → Writes article.aux with \citation{key} entries

Pass 2: biber article
  → Reads article.aux
  → Looks up keys in references.bib
  → Formats entries per biblatex style
  → Writes article.bbl

Pass 3: lualatex article.tex
  → Reads article.bbl
  → Resolves \cite{} commands
  → Writes page back-references

Pass 4: lualatex article.tex
  → Resolves remaining hyperlinks
  → Final PDF with clickable citations
```

**biber subprocess call:**
```python
result = subprocess.run(
    ["biber", tex_stem],   # e.g., biber article (no extension)
    cwd=output_dir,
    capture_output=True,
    text=True,
    timeout=120,
)
```

**biber error detection:**
```python
if result.returncode != 0:
    raise BibCompilationError(result.stderr)

biber_warnings = [
    line for line in result.stdout.splitlines()
    if "WARN" in line or "ERROR" in line
]
```

---

## 6. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Number of references | ≥ 5 | `len(references)` in `.bib` |
| biber exit code | 0 | `subprocess.returncode` |
| biber warnings | 0 | Scan stdout for `WARN` |
| Undefined citations | 0 | LaTeX log: `Citation ... undefined` |
| Orphaned .bib entries | 0 | biber log: `I didn't find a database entry for ...` |
| Clickable citation links | 100% | Manual PDF test: each [N] jumps to bibliography |
| Bibliography generation time | ≤ 1 second | Wall clock of `generate_bib()` |

---

## 7. Constraints

1. **biber only:** `bibtex` (legacy) MUST NOT be used. Only `biber` is permitted for Unicode support.
2. **biblatex only:** `natbib` MUST NOT be used. Only `biblatex` is permitted for hyperlink and Unicode support.
3. **Minimum 5 references:** The system MUST fail with a clear error if fewer than 5 valid references are provided.
4. **No orphaned entries:** Every `.bib` entry MUST be cited at least once in the article body.
5. **No duplicate keys:** Duplicate citation keys cause compilation failure; detected and raised at `generate_bib()` time.
6. **Bibliography is always last:** `\printbibliography` MUST be the final element before `\end{document}`.
7. **UTF-8 encoding:** `.bib` file MUST be saved as UTF-8. No Latin-1 or ASCII-only encoding.

---

## 8. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **BibTeX (legacy)** | No Unicode support — Hebrew author names and non-ASCII titles break compilation. `biber` is the modern, Unicode-capable replacement. |
| **natbib** | Author-year citation style package; does not integrate with `biblatex`; weaker Unicode and hyperlink support. |
| **Manual bibliography (`\begin{thebibliography}`)** | No `.bib` file, no automatic formatting, no clickable hyperlinks. Does not satisfy the assignment's citation linking requirement. |
| **Footnote-only citations** | Does not produce a consolidated bibliography section at the document end, violating Project.md §3 requirement. |
| **Zotero / Mendeley export** | Requires external tool; not automatable within the pipeline. `generate_bib()` produces `.bib` programmatically from agent output. |
| **`style=authoryear`** | Author-year style (Smith, 2024) is common in social sciences but numeric style [1] is more compact and standard in CS/engineering. |

---

## 9. Success Criteria

The bibliography system is considered successful when all of the following are true:

- [ ] `generate_bib()` produces a syntactically valid `.bib` file accepted by `biber` without errors.
- [ ] `.bib` file contains ≥ 5 entries, each with `author`, `title`, `year`, and type-appropriate fields.
- [ ] All citation keys are unique across the `.bib` file.
- [ ] `biber article` exits with code 0 and zero `WARN`/`ERROR` lines in stdout.
- [ ] Zero `Citation '...' undefined` warnings in the LaTeX `.log` after Pass 3.
- [ ] Zero orphaned `.bib` entries (every entry cited at least once).
- [ ] `\printbibliography` appears as the last section of the compiled PDF.
- [ ] Every `\cite{key}` in the PDF is a clickable hyperlink jumping to the bibliography entry.
- [ ] `.bib` file is saved as UTF-8; non-ASCII author names render correctly.
- [ ] `backref=true` — bibliography entries show page numbers where they are cited.

---

## 10. Test Scenarios

### Scenario T-001: Valid .bib round-trip
**Setup:** 5 `Reference` objects with all required fields  
**Action:** Call `generate_bib(references)`; run `biber article`  
**Expected:** biber exits 0; zero warnings; `.bbl` file produced with all 5 entries formatted

### Scenario T-002: Duplicate key detection
**Setup:** Two `Reference` objects with the same `key = "smith2020ai"`  
**Action:** Call `generate_bib(references)`  
**Expected:** `BibGenerationError` raised before any file is written; error message identifies the duplicate key

### Scenario T-003: Incomplete entry rejected
**Setup:** One `Reference` of type `"article"` with `journal = ""`  
**Action:** Call `generate_bib([ref])`  
**Expected:** `BibGenerationError` raised with message indicating missing `journal` field

### Scenario T-004: Fewer than 5 references rejected
**Setup:** List of 4 `Reference` objects (all valid)  
**Action:** Call `generate_bib(references)`  
**Expected:** `BibGenerationError` raised: "Minimum 5 references required, got 4"

### Scenario T-005: Unicode author names preserved
**Setup:** Reference with `author = "ברין, סרגיי and Page, Lawrence"`  
**Action:** Call `generate_bib([ref])`; inspect written `.bib` file  
**Expected:** Hebrew characters preserved in UTF-8 encoding; `biber` parses successfully

### Scenario T-006: All citations clickable in PDF
**Setup:** Full pipeline run with 5+ references  
**Action:** Open compiled PDF; click each `[N]` citation  
**Expected:** Each click navigates to the corresponding bibliography entry at document end

### Scenario T-007: Back-references in bibliography
**Setup:** Full pipeline with `backref=true` in preamble  
**Action:** Inspect bibliography section in compiled PDF  
**Expected:** Each bibliography entry shows "(cited on p. X)" back-reference

### Scenario T-008: Orphaned entry warning caught
**Setup:** `.bib` file with 6 entries, but only 5 cited in `.tex`  
**Action:** Run full 4-pass compilation; inspect biber log  
**Expected:** biber log contains warning for uncited entry; system logs this as a `CompilationResult.warnings` entry
