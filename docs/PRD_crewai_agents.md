# PRD_crewai_agents.md — Dedicated PRD: CrewAI Multi-Agent System
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Multi-Agent Systems (MAS)
A Multi-Agent System is a computational framework in which multiple autonomous agents — each with its own perception, reasoning, and action capabilities — collaborate to solve a problem that is too complex or too large for any single agent to handle alone. The key properties of MAS are:

- **Autonomy:** Each agent acts independently based on its goals and knowledge.
- **Specialization:** Each agent has a defined role and expertise domain.
- **Coordination:** Agents share information and results through defined protocols.
- **Decomposition:** The global task is decomposed into sub-tasks, each assigned to the most suitable agent.

In this project, the "problem too large for a single agent" is producing a professionally formatted, multi-element academic article. A single LLM call cannot simultaneously research a topic, write 15 pages, generate Python graph code, manage LaTeX preamble, handle BiDi, and format a bibliography. Decomposing into specialized agents allows each to focus on one concern.

### 1.2 CrewAI Framework
CrewAI is a Python framework for orchestrating role-playing AI agents. Its core abstractions are:

| Concept | Description |
|---------|-------------|
| `Agent` | An autonomous entity with a `role`, `goal`, `backstory`, and optional `tools`. The LLM is the agent's reasoning engine. |
| `Task` | A discrete unit of work assigned to a specific agent. Defines `description`, `expected_output`, and `context` (outputs from prior tasks). |
| `Crew` | The orchestrator that assembles agents and tasks and runs them in a defined `Process`. |
| `Process` | Execution strategy: `sequential` (tasks run in order, each output feeds next) or `hierarchical` (a manager agent delegates and verifies). |
| `Tool` | An external capability an agent can invoke — e.g., `SerperDevTool` for internet search, file I/O tools, custom Python tools. |

### 1.3 Sequential vs. Hierarchical Process
- **Sequential Process:** Tasks execute one by one. The output of Task N becomes `context` for Task N+1. Simple, predictable, deterministic ordering.
- **Hierarchical Process:** A manager LLM delegates tasks to worker agents, verifies outputs, and can re-assign if output is unsatisfactory. More flexible but adds token overhead.

**Choice for this project:** Sequential Process as primary (see ADR-001 in PLAN.md), with Hierarchical as a configurable fallback. Sequential is sufficient for the linear writing pipeline (research → write → review → format) and minimizes token usage.

### 1.4 Context Passing
In CrewAI Sequential mode, each `Task` receives the `output` of its listed `context` tasks. This is the core information-passing mechanism:

```
Researcher Task output → Writer Task context
Writer Task output     → Editor Task context
Editor Task output     → Graph Generator Task context
                       → LaTeX Formatter Task context
LaTeX Formatter output → BiDi Specialist Task context
```

This one-directional flow ensures each downstream agent builds on validated upstream work.

---

## 2. Agent Definitions

### 2.1 Mandatory Agents (per Project.md §2)

---

#### Agent 1: Researcher Agent

| Field | Value |
|-------|-------|
| **Class** | `ResearcherAgent` |
| **File** | `src/article_generator/services/agents/researcher.py` |
| **Mandatory** | YES — per Project.md §2 |
| **Role** | Senior Academic Researcher |
| **Goal** | Conduct thorough internet research and compile accurate, well-sourced data and key facts on the article topic |
| **Tools** | `SerperDevTool` (Google Search — **MANDATORY**) |
| **LLM access** | YES |

**Backstory:** You are a meticulous academic researcher with years of experience in literature reviews. You use search engines effectively to find credible sources, extract key facts, and organize information into structured outlines. You always cite your sources.

**Input:**
- Article topic (from `config/setup.json`)
- Target scope (~15 pages, Hebrew–English bilingual)

**Output:** A structured research outline including:
- Article title suggestion
- List of chapters/sections with brief descriptions
- Key facts, statistics, and claims per section
- List of ≥ 5 references (author, title, year, source) for the bibliography

**Tool usage constraint:** `SerperDevTool` is the ONLY tool assigned. The agent must use it to perform actual internet searches — not rely solely on parametric LLM knowledge.

**Performance metrics:**
- ≥ 3 distinct search queries executed
- ≥ 5 credible references found and cited
- Outline covers all mandatory sections (abstract, introduction, ≥ 4 chapters, conclusion)

---

#### Agent 2: Writer Agent

| Field | Value |
|-------|-------|
| **Class** | `WriterAgent` |
| **File** | `src/article_generator/services/agents/writer.py` |
| **Mandatory** | YES — per Project.md §2 |
| **Role** | Academic Article Writer |
| **Goal** | Transform the research outline into a complete, well-structured, ~15-page academic article in Markdown format |
| **Tools** | NONE — **no internet search tool** (per Project.md §2) |
| **LLM access** | YES |

**Backstory:** You are an experienced academic writer who excels at transforming raw research notes into clear, engaging scholarly articles. You write in both Hebrew and English, understand academic structure, and produce clean Markdown that converts well to LaTeX.

**Input (context):** Researcher agent's structured outline + reference list.

**Output:** Complete article in Markdown format including:
- Cover sheet metadata block (topic, author, date, course, lecturer)
- Abstract
- Introduction
- ≥ 4 substantive chapters
- At least one Markdown table (properly formatted for LaTeX `tabular`)
- At least one mathematical formula placeholder marked with `<!-- FORMULA: fancy LaTeX formula here -->`
- Conclusion
- Raw bibliography list

**Constraint:** This agent MUST NOT be assigned `SerperDevTool` or any other internet search tool. It relies entirely on the Researcher agent's context.

**Performance metrics:**
- Generated Markdown produces ≥ 15 pages when typeset in LaTeX at standard settings
- All mandatory sections present
- ≥ 1 table, ≥ 1 formula placeholder, ≥ 1 image reference

---

#### Agent 3: Reviewer / Quality Control Agent

| Field | Value |
|-------|-------|
| **Class** | `EditorAgent` |
| **File** | `src/article_generator/services/agents/editor.py` |
| **Mandatory** | YES — per Project.md §2 |
| **Role** | Academic Reviewer and Quality Controller |
| **Goal** | Check factual accuracy, improve text clarity and coherence, and ensure content quality — without changing the original meaning |
| **Tools** | NONE |
| **LLM access** | YES |

**Backstory:** You are a seasoned peer reviewer with a sharp eye for logical inconsistencies, unclear writing, and unsupported claims. You improve the text without rewriting it — you enhance clarity while preserving the author's intent.

**Input (context):** Writer agent's complete Markdown article.

**Output:** Revised Markdown article with:
- Improved clarity and coherence
- Factual inaccuracies flagged and corrected where possible
- Consistent academic tone throughout
- All structural elements preserved (table, formula placeholders, image refs intact)

**Performance metrics:**
- Output Markdown retains all sections from Writer output
- No structural elements removed (table, formula, image refs must survive review)
- Changes are improvements to existing text, not wholesale rewrites

---

#### Agent 4: LaTeX Generation Agent

| Field | Value |
|-------|-------|
| **Class** | `LaTeXFormatterAgent` |
| **File** | `src/article_generator/services/agents/latex_formatter.py` |
| **Mandatory** | YES — per Project.md §2 |
| **Role** | LaTeX Typesetting Specialist |
| **Goal** | Convert the approved Markdown article into complete, compilable LaTeX code ready for LuaLaTeX compilation |
| **Tools** | `FileWriterTool` — writes the final `.tex` file directly to `results/article.tex` |
| **LLM access** | YES |

**Skills:**
- `FileWriterTool` — allows the agent to **persist the `.tex` output to disk** itself, rather than returning it as a string for an external service to save. Ensures the file is written with correct UTF-8 encoding and the exact path expected by `LaTeXCompiler`.

**Backstory:** You are a LaTeX expert who specializes in academic typesetting, Hebrew–English bidirectional documents, and complex mathematical notation. You produce `.tex` files that compile on the first attempt.

**Input (context):** Reviewer agent's approved Markdown article.

**Output:** Complete `.tex` file including:
- Full preamble: `documentclass`, `usepackage` (polyglossia/babel, fancyhdr, hyperref, amsmath, graphicx, booktabs, geometry)
- Cover/title page (`\maketitle` or custom title block)
- `\tableofcontents`
- Chapter/section structure
- Headers and footers via `fancyhdr`
- At least one `equation` or `align` environment with a "fancy" formula (using `\frac`, `\sum`, `\int`, `\nabla`, etc.)
- At least one `tabular` or `tabularx` table within margins
- At least one `\includegraphics` referencing `assets/`
- `\cite{key}` commands for all bibliography references
- `\bibliography{references}` at the end

**Performance metrics:**
- Generated `.tex` compiles without errors (verified in LaTeX pipeline)
- All `\cite{}` keys match `.bib` entries
- No formula appears as plain text

---

### 2.2 Additional Agents (project-specific enhancements)

---

#### Agent 5: Graph Generator Agent

| Field | Value |
|-------|-------|
| **Class** | `GraphGeneratorAgent` |
| **File** | `src/article_generator/services/agents/graph_generator.py` |
| **Mandatory** | NO — enhances output quality |
| **Role** | Data Visualization Specialist |
| **Goal** | Produce clean, executable Python code that generates a meaningful data visualization relevant to the article topic |
| **Tools** | `CodeInterpreterTool` — executes Python code to test and iterate on graph generation |
| **LLM access** | YES |

**Skills:**
- `CodeInterpreterTool` — allows the agent to **run its own matplotlib code** and see the result. The agent iterates: write code → execute → observe output/error → fix → re-execute until the graph file is successfully produced. This eliminates blind code generation.

**Input (context):** Reviewer agent's Markdown (to understand the article topic and data).

**Output:** Executable Python code block (matplotlib/seaborn) that:
- Creates a figure relevant to the article content
- Saves it to `figures/graph.pdf` (or `.png`)
- Uses `plt.savefig()`, not `plt.show()`
- Is self-contained (all imports included)
- Has been verified to execute successfully via `CodeInterpreterTool`

**Performance metrics:**
- Code executes without errors (verified by the agent itself via `CodeInterpreterTool`)
- Output file exists at the declared path
- Figure is embedded in the final LaTeX document

---

#### Agent 6: BiDi Specialist Agent

| Field | Value |
|-------|-------|
| **Class** | `BiDiSpecialistAgent` |
| **File** | `src/article_generator/services/agents/bidi_specialist.py` |
| **Mandatory** | NO — ensures BiDi correctness |
| **Role** | Hebrew–English Bidirectional Text Specialist |
| **Goal** | Validate and correct all Hebrew–English direction switching in the `.tex` file; fix any formulas degraded to plain text due to BiDi confusion |
| **Tools** | `FileReadTool` — reads the `.tex` file; `FileWriterTool` — writes the corrected `.tex` file |
| **LLM access** | YES |

**Skills:**
- `FileReadTool` — reads `results/article.tex` directly from disk for validation, rather than relying on in-memory context (which may be truncated for large documents).
- `FileWriterTool` — writes the BiDi-corrected `.tex` back to `results/article.tex`, overwriting the previous version with the validated content.

**Input (context):** LaTeX Formatter agent's `.tex` file.

**Output:** Corrected `.tex` file with:
- Proper `\LR{...}` and `\RL{...}` (or equivalent) wrapping where direction switches
- All formulas verified as LaTeX math environments (no plain-text degradation)
- At least one chapter demonstrating correct RTL ↔ LTR transition

**Performance metrics:**
- No "formula as plain text" issues in final PDF
- Hebrew text renders RTL; English text renders LTR within the same document
- No garbled characters in compiled PDF

---

## 2.3 Agent Skills + Tools Summary

Each agent has two distinct components:
- **Skill** — a `SKILL.md` folder injected via `skills=["./skills/<name>"]`, providing behavioral guidelines
- **Tools** — Python `crewai_tools` instances assigned via `tools=[...]`

| Agent | Skill folder | Tools (`crewai_tools`) |
|-------|-------------|------------------------|
| `ResearcherAgent` | `skills/researcher/` | `SerperDevTool` |
| `WriterAgent` | `skills/writer/` | — |
| `EditorAgent` | `skills/editor/` | — |
| `GraphGeneratorAgent` | `skills/graph_generator/` | `CodeInterpreterTool` |
| `LaTeXFormatterAgent` | `skills/latex_formatter/` | `FileWriterTool` |
| `BiDiSpecialistAgent` | `skills/bidi_specialist/` | `FileReadTool`, `FileWriterTool` |

> **Search isolation rule:** Only `ResearcherAgent` has `SerperDevTool`. All other agents are forbidden from having any internet search tool.  
> **Non-search tools** (`FileReadTool`, `FileWriterTool`, `CodeInterpreterTool`) are assigned where the agent's task requires direct file access or code execution.

---

## 3. Task Definitions

Each CrewAI `Task` has a `description`, `expected_output`, assigned `agent`, and `context` (list of prior tasks whose output feeds this task).

| Task # | Name | Agent | Context from | Expected Output |
|--------|------|-------|--------------|-----------------|
| Task 1 | `research_task` | ResearcherAgent | — | Structured research outline + ≥ 5 references |
| Task 2 | `write_task` | WriterAgent | Task 1 | Complete Markdown article (~15 pages) |
| Task 3 | `review_task` | EditorAgent | Task 2 | Revised and quality-checked Markdown |
| Task 4 | `graph_task` | GraphGeneratorAgent | Task 3 | Executable Python graph code |
| Task 5 | `latex_task` | LaTeXFormatterAgent | Task 3 | Complete `.tex` file |
| Task 6 | `bidi_task` | BiDiSpecialistAgent | Task 5 | Validated and corrected `.tex` file |

> Note: Tasks 4 and 5 both receive context from Task 3 (the reviewed Markdown). Task 6 receives context from Task 5 (the `.tex` file).

---

## 4. Crew Configuration

### 4.1 Crew Object
```python
crew = Crew(
    agents=[
        researcher_agent,
        writer_agent,
        editor_agent,
        graph_generator_agent,
        latex_formatter_agent,
        bidi_specialist_agent,
    ],
    tasks=[
        research_task,
        write_task,
        review_task,
        graph_task,
        latex_task,
        bidi_task,
    ],
    process=Process.sequential,   # or Process.hierarchical (configurable)
    verbose=True,
)
```

### 4.2 Process Configuration (from `config/setup.json`)
```json
{
  "crew": {
    "process": "sequential",
    "verbose": true,
    "max_rpm": 30
  }
}
```

---

## 5. Input / Output Contract

### 5.1 System Input
| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `topic` | `config/setup.json` | `str` | Article subject |
| `author` | `config/setup.json` | `str` | Author name for cover sheet |
| `course` | `config/setup.json` | `str` | Course name |
| `lecturer` | `config/setup.json` | `str` | Lecturer name |
| `LLM_API_KEY` | `.env` | `str` | LLM provider API key |
| `SERPER_API_KEY` | `.env` | `str` | Serper Google Search API key |

### 5.2 System Output
| Output | Type | Location | Description |
|--------|------|----------|-------------|
| Research outline | `str` (Markdown) | in-memory | Researcher task output |
| Draft article | `str` (Markdown) | in-memory | Writer task output |
| Reviewed article | `str` (Markdown) | `data/article_reviewed.md` | Editor task output |
| Graph Python code | `str` (Python) | in-memory | Graph Generator output |
| Graph figure | `file` (PNG/PDF) | `assets/article_graph.png` | Executed by GraphRunner |
| LaTeX source | `str` (.tex) | `results/article.tex` | LaTeX Formatter output |
| BiDi-validated LaTeX | `str` (.tex) | `results/article.tex` | BiDi Specialist output |

---

## 6. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pipeline completion time | ≤ 30 minutes | Wall clock from `crew.kickoff()` to `ArticleResult` |
| Researcher search queries | ≥ 3 queries | Count of `SerperDevTool` invocations logged |
| References found | ≥ 5 | Count in `.bib` file |
| Article length | ≥ 15 pages | PDF page count |
| Task success rate | 100% (all 6 tasks complete) | No task raises unhandled exception |
| LLM API calls per run | tracked | `ApiGatekeeper.get_token_stats()` |

---

## 7. Constraints

1. **Search tool isolation:** `SerperDevTool` (and any internet search tool) MUST be assigned ONLY to `ResearcherAgent`. No other agent MAY have an internet search tool. Non-search tools (`FileReadTool`, `FileWriterTool`, `CodeInterpreterTool`) are permitted on appropriate agents.
2. **Context chaining:** Every task (except Task 1) MUST declare `context` from at least one prior task. Agents MUST NOT ignore context.
3. **Process type:** Crew MUST use `Process.sequential` or `Process.hierarchical`. No other process type is permitted.
4. **No business logic in Crew layer:** `CrewService` delegates to `ArticleGeneratorSDK`; agent definitions contain only CrewAI configuration — no file I/O, no LaTeX compilation.
5. **File size:** Each agent file MUST NOT exceed 150 lines of code.
6. **API calls via Gatekeeper:** Even though CrewAI internally calls the LLM, all external calls MUST be wrapped through `ApiGatekeeper` (via a custom LLM callback or middleware).

---

## 8. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **Single-agent monolith** | One LLM call cannot reliably produce a 15-page structured article with all visual elements, BiDi, and bibliography in one shot. Output quality degrades with prompt complexity. |
| **LangGraph** | More powerful for cyclic/conditional flows but significantly more complex setup. The linear pipeline does not need graph-based state machines. |
| **AutoGen (Microsoft)** | Multi-agent conversation framework; less clean task handoff model; requires more boilerplate; not aligned with assignment requirement specifying CrewAI. |
| **Plain LangChain agents** | No native crew/task abstraction; would require manual context-passing implementation; CrewAI provides this out of the box. |
| **Parallel task execution** | Tasks 2–6 depend on prior tasks' context; parallel execution is not possible without breaking the dependency chain. |

---

## 9. Success Criteria

The CrewAI multi-agent system is considered successful when all of the following are true:

- [ ] All 6 tasks complete without raising an unhandled exception.
- [ ] `research_task` output contains ≥ 5 references with author/title/year.
- [ ] `write_task` output is valid Markdown with all mandatory sections (abstract, introduction, ≥ 4 chapters, conclusion, bibliography list).
- [ ] `write_task` output contains ≥ 1 table, ≥ 1 formula placeholder, ≥ 1 image reference.
- [ ] `review_task` output preserves all structural elements from Writer output.
- [ ] `graph_task` output is executable Python code that runs without errors.
- [ ] `latex_task` output is a complete `.tex` file that compiles with LuaLaTeX.
- [ ] `bidi_task` output contains no plain-text formula degradation.
- [ ] ResearcherAgent made ≥ 3 internet searches via `SerperDevTool`.
- [ ] WriterAgent has no internet search tool assigned.
- [ ] All LLM calls are logged as `CallRecord` objects in `ApiGatekeeper`.

---

## 10. Test Scenarios

### Scenario T-001: Researcher performs live internet search
**Setup:** Valid `SERPER_API_KEY` in `.env`; topic = "Artificial Intelligence in Education"  
**Action:** Run `research_task` only  
**Expected:** ≥ 3 `SerperDevTool` invocations logged; output contains ≥ 5 references with URLs/sources; no references are fabricated (hallucinated)

### Scenario T-002: Writer receives Researcher context
**Setup:** Mock `research_task` output with a structured outline  
**Action:** Run `write_task` with mock context  
**Expected:** Output Markdown references content from the mock outline; sections align with outlined chapters; table and formula placeholder present

### Scenario T-003: Writer has no internet tool
**Setup:** Inspect `writer_agent.tools`  
**Action:** Assert `writer_agent.tools == []`  
**Expected:** No `SerperDevTool` or any search tool in Writer's tool list; test passes without running LLM

### Scenario T-004: Reviewer preserves structural elements
**Setup:** Mock `write_task` output with a table and formula  
**Action:** Run `review_task` with mock context  
**Expected:** Output Markdown still contains the table and formula placeholder; no structural elements removed

### Scenario T-005: LaTeX Formatter produces compilable .tex
**Setup:** Mock `review_task` output with full Markdown article  
**Action:** Run `latex_task`; pass output to `LaTeXCompiler.compile()`  
**Expected:** `compile()` returns `CompilationResult(success=True)`; no LaTeX errors in log

### Scenario T-006: BiDi Specialist fixes plain-text formula
**Setup:** Inject a `.tex` snippet containing `sigma(x) = sum_i w_i * x_i` (plain text formula)  
**Action:** Run `bidi_task` with the injected context  
**Expected:** Output `.tex` replaces plain-text formula with proper LaTeX math environment

### Scenario T-007: Full crew pipeline completes end-to-end (mocked LLM)
**Setup:** Mock all LLM calls with deterministic responses; mock `SerperDevTool` with fake results  
**Action:** Run `crew.kickoff()`  
**Expected:** All 6 tasks complete; `ArticleResult` populated with non-empty content; no exceptions raised

### Scenario T-008: Pipeline resilience — API rate limit on Task 2
**Setup:** Configure `ApiGatekeeper` to simulate rate limit on the 2nd call  
**Action:** Run full crew pipeline  
**Expected:** Writer task queues the call; pipeline resumes after queue drain; no task fails due to rate limit
