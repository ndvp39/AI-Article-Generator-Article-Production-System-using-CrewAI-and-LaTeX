# PRD_skills.md — Dedicated PRD: Agent Skills & Tools
# AI Article Generator

**Version:** 1.01  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Tools vs. Skills — The Distinction

In the CrewAI framework, agents can be extended with two categories of capabilities:

| Category | What it is | Examples |
|----------|-----------|---------|
| **Tools** | Generic, reusable integrations from `crewai_tools` | `SerperDevTool`, `FileWriterTool`, `CodeInterpreterTool` |
| **Skills** | Custom `BaseTool` subclasses that encode domain-specific logic for this project | `MarkdownToLatexSkill`, `BiDiScannerSkill`, `GraphCodeValidatorSkill` |

**Tools** are off-the-shelf: they are imported from `crewai_tools` and handle general operations (search, file I/O, code execution). They have no knowledge of article generation, LaTeX, or Hebrew BiDi.

**Skills** are project-specific: they are written as `BaseTool` subclasses in `src/article_generator/services/tools/skills/` and encode the exact domain logic needed for each agent's task. A skill gives the agent a structured, reliable capability it can invoke by name — rather than asking it to re-derive the logic from text instructions every time.

### 1.2 Why Custom Skills?

Without custom skills, agents must reason through complex multi-step operations using only their LLM reasoning. This leads to:
- **Inconsistent outputs** — the LLM may format references differently each run
- **Missed checks** — the LLM may forget to validate a constraint under a long context
- **Brittle logic** — complex transformations (Markdown → LaTeX, BiDi scanning) encoded in prompts break when the model changes

With custom skills:
- The logic is in deterministic Python code — always runs the same way
- The agent calls the skill like a function: input in, structured output out
- Tests cover the skill in isolation — independent of the LLM

### 1.3 Anatomy of a SKILL.md File

Each skill is an **independent folder** at the project root containing a single file strictly named `SKILL.md`. The file MUST begin with a YAML metadata block enclosed by `---`, followed by Markdown behavioral guidelines.

```
skills/
├── researcher/
│   └── SKILL.md
├── writer/
│   └── SKILL.md
...
```

**SKILL.md structure:**

```markdown
---
name: "Human-readable skill name"
description: "One-line description of what this skill guides the agent to do."
author: "AI Article Generator — HW3, Dr. Yoram Segal"
version: "1.0.0"
---

## Role
[What the agent is and its purpose]

## Workflow
[Step-by-step instructions the agent follows]

## Constraints
[Hard rules the agent MUST NOT violate]
```

**Injection into an agent** is done via the `skills=` parameter at agent construction:

```python
from crewai import Agent

agent = Agent(
    role="Senior Academic Researcher",
    goal="...",
    backstory="...",
    tools=[SerperDevTool()],
    skills=["./skills/researcher"],   # path to the skill folder
)
```

The contents of `SKILL.md` are injected into the agent's context, shaping its behavior deterministically — without relying on the LLM to re-derive the logic from generic instructions each run.

### 1.4 Skill File Layout

```
skills/                              ← project root — active skill folders
├── researcher/
│   └── SKILL.md                     ← ResearcherAgent behavioral guidelines
├── writer/
│   └── SKILL.md                     ← WriterAgent behavioral guidelines
├── editor/
│   └── SKILL.md                     ← EditorAgent behavioral guidelines
├── graph_generator/
│   └── SKILL.md                     ← GraphGeneratorAgent behavioral guidelines
├── latex_formatter/
│   └── SKILL.md                     ← LaTeXFormatterAgent behavioral guidelines
└── bidi_specialist/
    └── SKILL.md                     ← BiDiSpecialistAgent behavioral guidelines

docs/skills/                         ← developer reference documentation only
├── researcher_skills.md
├── writer_skills.md
...
```

---

## 2. Generic Tools (from `crewai_tools`)

### 2.1 Tools Summary

| Tool | Package | Assigned to | Purpose |
|------|---------|-------------|---------|
| `SerperDevTool` | `crewai_tools` | ResearcherAgent | Live Google search via Serper API |
| `CodeInterpreterTool` | `crewai_tools` | GraphGeneratorAgent | Executes Python code; returns stdout/stderr |
| `FileReadTool` | `crewai_tools` | BiDiSpecialistAgent | Reads file from disk as UTF-8 string |
| `FileWriterTool` | `crewai_tools` | LaTeXFormatterAgent, BiDiSpecialistAgent | Writes content to file on disk |

### 2.2 Tool Isolation Rule

`SerperDevTool` is the only **internet search tool** and MUST only be on `ResearcherAgent`. File and code tools may be assigned to any agent that needs them.

`validate_tool_isolation()` in `search_tools.py` enforces this at crew startup:

```python
SEARCH_TOOLS = {"SerperDevTool", "WebsiteSearchTool", "DuckDuckGoSearchTool"}

def validate_tool_isolation(agents: list[Agent]) -> None:
    for agent in agents:
        if agent.role != "Senior Research Specialist":
            tool_names = {type(t).__name__ for t in agent.tools}
            if violations := tool_names & SEARCH_TOOLS:
                raise ToolIsolationError(
                    f"Agent '{agent.role}' has search tool(s) {violations}"
                )
```

---

## 3. Custom Skills (per-agent `BaseTool` subclasses)

---

### 3.1 `ExtractReferencesSkill` — ResearcherAgent

**File:** `src/article_generator/services/tools/skills/extract_references.py`  
**Agent:** `ResearcherAgent`  
**Purpose:** Parses raw search result snippets and extracts structured `Reference` objects (author, title, year, URL, type).

```python
class ExtractReferencesInput(BaseModel):
    search_results_text: str = Field(
        description="Raw text of search results containing academic sources"
    )

class ExtractReferencesSkill(BaseTool):
    name: str = "Extract References"
    description: str = (
        "Parse raw search results and extract structured academic references. "
        "Returns a JSON list of references with author, title, year, url, and type fields. "
        "Use this after collecting search results to format them for the bibliography."
    )
    args_schema: type[BaseModel] = ExtractReferencesInput

    def _run(self, search_results_text: str) -> str:
        # Regex + heuristics to extract: author, title, year, URL, entry_type
        # Returns JSON: [{"key": "...", "author": "...", "title": "...", ...}]
        references = self._parse_references(search_results_text)
        return json.dumps([asdict(r) for r in references], ensure_ascii=False)
```

**What it enables:** The Researcher agent can call this skill after every search to convert raw snippets into clean, validated `Reference` objects ready for the `.bib` file — without asking the LLM to do text parsing.

---

### 3.2 `ArticleStructureValidatorSkill` — WriterAgent

**File:** `src/article_generator/services/tools/skills/article_structure.py`  
**Agent:** `WriterAgent`  
**Purpose:** Validates that a Markdown article contains all mandatory structural sections before the agent considers its task complete.

```python
REQUIRED_SECTIONS = [
    "abstract", "introduction", "conclusion"
]
REQUIRED_ELEMENTS = ["| ", "$$", "<!-- FORMULA", "[GRAPH:"]

class ArticleStructureInput(BaseModel):
    markdown_content: str = Field(description="The full Markdown article to validate")

class ArticleStructureValidatorSkill(BaseTool):
    name: str = "Validate Article Structure"
    description: str = (
        "Check that a Markdown article contains all required sections: "
        "abstract, introduction, ≥4 body chapters, conclusion, and required elements "
        "(table, formula, graph placeholder). Returns a validation report. "
        "Call this before finalizing the article to catch missing sections."
    )
    args_schema: type[BaseModel] = ArticleStructureInput

    def _run(self, markdown_content: str) -> str:
        issues = []
        lower = markdown_content.lower()
        for section in REQUIRED_SECTIONS:
            if f"## {section}" not in lower and f"# {section}" not in lower:
                issues.append(f"Missing section: {section}")
        chapter_count = lower.count("\n## ")
        if chapter_count < 4:
            issues.append(f"Only {chapter_count} chapters — need ≥ 4")
        for element in REQUIRED_ELEMENTS:
            if element not in markdown_content:
                issues.append(f"Missing required element: {element!r}")
        if issues:
            return "VALIDATION FAILED:\n" + "\n".join(f"- {i}" for i in issues)
        return "VALIDATION PASSED: All required sections and elements present."
```

**What it enables:** The Writer agent can self-check its output before returning it, catching missing sections without needing the LLM to re-read the whole document.

---

### 3.3 `AcademicQualityCheckerSkill` — EditorAgent

**File:** `src/article_generator/services/tools/skills/quality_checker.py`  
**Agent:** `EditorAgent`  
**Purpose:** Scans the article for common academic writing quality issues: unsupported claims, plain-text formulas, inconsistent citation format, and weak language patterns.

```python
PLAIN_TEXT_FORMULA_PATTERNS = [
    r"\bsigma\b", r"\bintegral\b", r"\bsummation\b", r"\bdelta\b",
    r"\balpha\b", r"\bbeta\b", r"\btheta\b",
]
WEAK_PATTERNS = [r"\bvery\b", r"\bquite\b", r"\bbasically\b", r"\bobviously\b"]

class QualityCheckerInput(BaseModel):
    markdown_content: str = Field(description="Article Markdown to quality-check")

class AcademicQualityCheckerSkill(BaseTool):
    name: str = "Academic Quality Checker"
    description: str = (
        "Scan an article for quality issues: plain-text formulas (words like 'sigma', "
        "'integral'), weak language ('very', 'basically'), and missing citation markers. "
        "Returns a list of issues with line numbers. Use this to identify problems "
        "before making targeted improvements."
    )
    args_schema: type[BaseModel] = QualityCheckerInput

    def _run(self, markdown_content: str) -> str:
        issues = []
        for i, line in enumerate(markdown_content.splitlines(), 1):
            for pattern in PLAIN_TEXT_FORMULA_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: plain-text formula word — use LaTeX math")
            for pattern in WEAK_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: weak academic language — consider revising")
        return "\n".join(issues) if issues else "No quality issues found."
```

**What it enables:** The Editor agent gets a structured issue list it can work through systematically, rather than asking the LLM to spot everything in one read.

---

### 3.4 `GraphCodeValidatorSkill` — GraphGeneratorAgent

**File:** `src/article_generator/services/tools/skills/graph_validator.py`  
**Agent:** `GraphGeneratorAgent`  
**Purpose:** Static-validates generated Python code before passing it to `CodeInterpreterTool` — catches `plt.show()`, missing axis labels, missing `matplotlib.use("Agg")`, and security violations.

```python
FORBIDDEN_PATTERNS = ["plt.show()", "os.system(", "subprocess.", "eval(", "exec("]
REQUIRED_PATTERNS  = ['matplotlib.use("Agg")', "plt.savefig(", "set_xlabel", "set_ylabel"]

class GraphValidatorInput(BaseModel):
    python_code: str = Field(description="Python graph code to validate before execution")

class GraphCodeValidatorSkill(BaseTool):
    name: str = "Validate Graph Code"
    description: str = (
        "Static-check Python matplotlib code for correctness before execution. "
        "Checks for: plt.show() (forbidden), missing Agg backend, missing axis labels, "
        "and security violations. Returns VALID or a list of issues to fix. "
        "Always call this before running code with CodeInterpreterTool."
    )
    args_schema: type[BaseModel] = GraphValidatorInput

    def _run(self, python_code: str) -> str:
        issues = []
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in python_code:
                issues.append(f"FORBIDDEN: {pattern!r} found in code")
        for pattern in REQUIRED_PATTERNS:
            if pattern not in python_code:
                issues.append(f"MISSING: {pattern!r} required in code")
        try:
            ast.parse(python_code)
        except SyntaxError as e:
            issues.append(f"SYNTAX ERROR: {e}")
        return "\n".join(issues) if issues else "VALID: Code passes all checks."
```

**What it enables:** The agent validates BEFORE executing — fast pre-check catches 90% of issues without spending `CodeInterpreterTool` execution time.

---

### 3.5 `MarkdownToLatexSkill` — LaTeXFormatterAgent

**File:** `src/article_generator/services/tools/skills/markdown_to_latex.py`  
**Agent:** `LaTeXFormatterAgent`  
**Purpose:** Converts common Markdown constructs to LaTeX equivalents — headings, bold/italic, tables, code blocks, citation markers.

```python
class MarkdownToLatexInput(BaseModel):
    markdown_fragment: str = Field(
        description="A Markdown fragment (paragraph, table, heading) to convert to LaTeX"
    )

class MarkdownToLatexSkill(BaseTool):
    name: str = "Convert Markdown to LaTeX"
    description: str = (
        "Convert a Markdown fragment to its LaTeX equivalent. Handles: "
        "## headings → \\section{}, **bold** → \\textbf{}, *italic* → \\textit{}, "
        "| tables | → tabularx, [AuthorYear] → \\cite{authoryear}, "
        "```code``` → \\begin{verbatim}. Use this for each section of the article."
    )
    args_schema: type[BaseModel] = MarkdownToLatexInput

    def _run(self, markdown_fragment: str) -> str:
        text = markdown_fragment
        # Headings
        text = re.sub(r"^### (.+)$", r"\\subsection{\1}", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$",  r"\\section{\1}",    text, flags=re.MULTILINE)
        text = re.sub(r"^# (.+)$",   r"\\chapter{\1}",    text, flags=re.MULTILINE)
        # Inline formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
        text = re.sub(r"\*(.+?)\*",     r"\\textit{\1}", text)
        # Citations: [AuthorYear] → \cite{authoryear}
        text = re.sub(r"\[([A-Z][a-z]+\d{4}\w*)\]", lambda m: f"\\cite{{{m.group(1).lower()}}}", text)
        return text
```

**What it enables:** The LaTeX Formatter agent converts the article piece by piece with deterministic, testable transformations — not asking the LLM to memorize conversion rules under a huge context.

---

### 3.6 `BiDiScannerSkill` — BiDiSpecialistAgent

**File:** `src/article_generator/services/tools/skills/bidi_scanner.py`  
**Agent:** `BiDiSpecialistAgent`  
**Purpose:** Scans a LaTeX document for all BiDi issues: bare Hebrew text, unguarded inline math in `hebrew` environments, and tables inside RTL blocks.

```python
HEBREW_RANGE = re.compile(r"[֐-׿]")
INSIDE_HEBREW_ENV = re.compile(
    r"\\begin\{hebrew\}(.*?)\\end\{hebrew\}", re.DOTALL
)

class BiDiScannerInput(BaseModel):
    latex_content: str = Field(description="Full .tex document content to scan for BiDi issues")

class BiDiScannerSkill(BaseTool):
    name: str = "Scan LaTeX for BiDi Issues"
    description: str = (
        "Scan a LaTeX document and return all bidirectional text issues: "
        "(1) Hebrew characters outside \\begin{hebrew} environments, "
        "(2) inline math $...$ inside hebrew environments without \\LRE{} wrapping, "
        "(3) \\begin{table} or \\begin{tabular} inside hebrew environments. "
        "Returns a JSON list of {line, type, fragment} objects."
    )
    args_schema: type[BaseModel] = BiDiScannerInput

    def _run(self, latex_content: str) -> str:
        issues = []
        lines = latex_content.splitlines()

        # Check 1: bare Hebrew outside any hebrew env
        hebrew_envs = set()
        in_hebrew = False
        for i, line in enumerate(lines, 1):
            if r"\begin{hebrew}" in line:
                in_hebrew = True
            if r"\end{hebrew}" in line:
                in_hebrew = False
            if not in_hebrew and HEBREW_RANGE.search(line):
                issues.append({"line": i, "type": "bare_hebrew", "fragment": line.strip()})

        # Check 2: unguarded inline math inside hebrew env
        for match in INSIDE_HEBREW_ENV.finditer(latex_content):
            block = match.group(1)
            for m in re.finditer(r"(?<!\\LRE\{)\$[^$]+\$", block):
                issues.append({"line": "in hebrew block", "type": "unguarded_math",
                                "fragment": m.group()})

        # Check 3: table inside hebrew env
        for match in INSIDE_HEBREW_ENV.finditer(latex_content):
            block = match.group(1)
            if r"\begin{table}" in block or r"\begin{tabular}" in block:
                issues.append({"line": "in hebrew block", "type": "rtl_table",
                                "fragment": "table inside hebrew env"})

        return json.dumps(issues, ensure_ascii=False) if issues else "[]"
```

**What it enables:** The BiDi Specialist gets a precise, machine-generated list of issues to fix — no relying on the LLM to notice subtle Unicode direction characters or missing `\LRE{}` wrappers.

---

## 4. Complete Agent Skills + Tools Matrix

| Agent | SKILL.md folder | Generic Tools |
|-------|----------------|---------------|
| `ResearcherAgent` | `skills/researcher/` | `SerperDevTool` |
| `WriterAgent` | `skills/writer/` | — |
| `EditorAgent` | `skills/editor/` | — |
| `GraphGeneratorAgent` | `skills/graph_generator/` | `CodeInterpreterTool` |
| `LaTeXFormatterAgent` | `skills/latex_formatter/` | `FileWriterTool` |
| `BiDiSpecialistAgent` | `skills/bidi_specialist/` | `FileReadTool`, `FileWriterTool` |

---

## 5. Agent Construction with Skills + Tools

Each agent is constructed with:
- `skills=["./skills/<name>"]` — injects the SKILL.md behavioral guidelines
- `tools=[...]` — Python crewai_tools assigned to the agent

```python
from crewai import Agent
from crewai_tools import SerperDevTool, CodeInterpreterTool, FileReadTool, FileWriterTool

# researcher.py
Agent(
    role="Senior Academic Researcher", ...,
    tools=[SerperDevTool()],
    skills=["./skills/researcher"],
)

# writer.py
Agent(
    role="Academic Article Writer", ...,
    tools=[],
    skills=["./skills/writer"],
)

# editor.py
Agent(
    role="Academic Reviewer and Quality Controller", ...,
    tools=[],
    skills=["./skills/editor"],
)

# graph_generator.py
Agent(
    role="Data Visualization Specialist", ...,
    tools=[CodeInterpreterTool()],
    skills=["./skills/graph_generator"],
)

# latex_formatter.py
Agent(
    role="LaTeX Typesetting Specialist", ...,
    tools=[FileWriterTool()],
    skills=["./skills/latex_formatter"],
)

# bidi_specialist.py
Agent(
    role="Hebrew–English Bidirectional Text Specialist", ...,
    tools=[FileReadTool(), FileWriterTool()],
    skills=["./skills/bidi_specialist"],
)
```

---

## 6. Requirements

**REQ-SKILL-01:** Each agent MUST be constructed with a `skills=["./skills/<name>"]` parameter pointing to its skill folder.  
**REQ-SKILL-02:** Each skill folder MUST contain a file named exactly `SKILL.md` — no other name is valid.  
**REQ-SKILL-03:** Every `SKILL.md` MUST begin with a YAML block (`---`) containing `name`, `description`, `author`, and `version`.  
**REQ-SKILL-04:** Skill guidelines MUST include a **Workflow** section and a **Constraints** section.  
**REQ-SKILL-05:** Skills MUST NOT contain Python code — behavioral guidelines only.  
**REQ-SKILL-06:** The `GraphGeneratorAgent` SKILL.md MUST instruct the agent to validate code with `GraphCodeValidator` before running `CodeInterpreterTool`.  
**REQ-SKILL-07:** The `BiDiSpecialistAgent` SKILL.md MUST instruct the agent to run `BiDiScanner` before and after applying fixes.

---

## 7. Test Scenarios

### Scenario T-001: ExtractReferencesSkill parses search results
**Input:** Text block with 3 academic source snippets  
**Expected:** Returns JSON with 3 `Reference` objects, each with `author`, `title`, `year`, `url`

### Scenario T-002: ArticleStructureValidatorSkill catches missing section
**Input:** Markdown article missing `## Conclusion`  
**Expected:** Returns "VALIDATION FAILED" with "Missing section: conclusion"

### Scenario T-003: AcademicQualityCheckerSkill catches plain-text formula
**Input:** Article line: "The value of sigma increases with noise"  
**Expected:** Returns issue at correct line: "plain-text formula word — use LaTeX math"

### Scenario T-004: GraphCodeValidatorSkill catches plt.show()
**Input:** Python code containing `plt.show()`  
**Expected:** Returns "FORBIDDEN: 'plt.show()' found in code"

### Scenario T-005: GraphCodeValidatorSkill passes valid code
**Input:** Complete valid matplotlib script per §6 of PRD_graph_generation.md  
**Expected:** Returns "VALID: Code passes all checks."

### Scenario T-006: MarkdownToLatexSkill converts headings
**Input:** `## Deep Learning`  
**Expected:** Returns `\section{Deep Learning}`

### Scenario T-007: MarkdownToLatexSkill converts citation markers
**Input:** `as shown by [Vaswani2017]`  
**Expected:** Returns `as shown by \cite{vaswani2017}`

### Scenario T-008: BiDiScannerSkill detects bare Hebrew
**Input:** `.tex` file with `שלום` outside any `\begin{hebrew}` environment  
**Expected:** Returns JSON with one issue: `{"type": "bare_hebrew", ...}`

### Scenario T-009: BiDiScannerSkill returns empty list for clean file
**Input:** Correctly structured `.tex` with all Hebrew inside `\begin{hebrew}` blocks  
**Expected:** Returns `"[]"`

### Scenario T-010: All agent tools lists correct at runtime
**Setup:** Build all 6 agents  
**Action:** Inspect `agent.tools` for each  
**Expected:** Tool names match §4 matrix exactly; `validate_tool_isolation()` raises no errors
