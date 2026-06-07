# TODO.md — Tasks Document
# AI Article Generator: Academic Article Production System

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## Legend

| Status | Meaning |
|--------|---------|
| `[ ]` | Not Started |
| `[~]` | In Progress |
| `[x]` | Done |

| Priority | Meaning |
|----------|---------|
| `HIGH` | Critical path — blocks other tasks |
| `MED` | Important, non-blocking |
| `LOW` | Polish / nice-to-have |

**Owner:** Developer (student) for all tasks unless noted otherwise.

---

## Phase 1 — Documentation (Milestone M1)

> **Goal:** All documentation created and approved before any line of code is written.  
> **Exit Criteria:** PRD.md, PLAN.md, TODO.md, and all dedicated PRDs reviewed and consistent with each other.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-001 | Create `docs/PRD.md` — main Product Requirements Document | `HIGH` | `[x]` | Developer | File exists; all 7 sections complete; no contradictions with Project.md |
| T-002 | Create `docs/PLAN.md` — Architecture & Design Document | `HIGH` | `[x]` | Developer | C4 diagrams (4 levels), UML sequence + class + deployment, all ADRs, full data schemas |
| T-003 | Create `docs/TODO.md` — this file | `HIGH` | `[x]` | Developer | All tasks listed with phase, priority, status, owner, DoD |
| T-004 | Create `docs/PRD_crewai_agents.md` — dedicated PRD for multi-agent system | `HIGH` | `[x]` | Developer | Includes theoretical background, all 6 agents specified, I/O contracts, tool assignments, success criteria, test scenarios |
| T-005 | Create `docs/PRD_latex_pipeline.md` — dedicated PRD for LaTeX generation & compilation | `HIGH` | `[x]` | Developer | Covers .tex generation, preamble requirements, 4-pass compilation, BiDi engine choice, error handling |
| T-006 | Create `docs/PRD_api_gatekeeper.md` — dedicated PRD for API Gatekeeper | `HIGH` | `[x]` | Developer | Rate limiting spec, FIFO queue design, retry policy, CallRecord schema, test scenarios |
| T-007 | Create `docs/PRD_bibliography.md` — dedicated PRD for bibliography management | `HIGH` | `[x]` | Developer | .bib file format, BibTeX/biber workflow, \cite{} linking, clickability requirements |
| T-008 | Create `docs/PRD_bidi.md` — dedicated PRD for Hebrew–English BiDi | `HIGH` | `[x]` | Developer | polyglossia/babel setup, RTL/LTR switching, formula degradation fix procedure |
| T-009 | Create `docs/PRD_graph_generation.md` — dedicated PRD for Python graph generation | `MED` | `[x]` | Developer | matplotlib spec, programmatic execution, output path, LaTeX embedding |
| T-010 | Create `docs/PRD_cost_tracker.md` — dedicated PRD for token tracking & cost analysis | `MED` | `[x]` | Developer | CallRecord schema, per-agent breakdown, cross-model comparison, budget alert, report format |
| T-011 | Create `docs/PRD_research_tools.md` — dedicated PRD for SerperDevTool internet search | `HIGH` | `[x]` | Developer | SerperDevTool integration, SERPER_API_KEY management, tool isolation rule, test scenarios |
| T-011b | Create `docs/PRD_skills.md` — dedicated PRD for all agent skills/tools (custom skills + generic tools per agent) | `HIGH` | `[x]` | Developer |
| T-011c | Create `skills/` at project root — one `SKILL.md` per agent (YAML frontmatter + Markdown guidelines, injected via `skills=` param) | `HIGH` | `[x]` | Developer | 6 folders: researcher, writer, editor, graph_generator, latex_formatter, bidi_specialist — each with SKILL.md containing name/description/author/version + Workflow + Constraints |
| T-012 | Create `README.md` — full user manual at project root | `HIGH` | `[x]` | Developer | Installation, usage, examples, config guide, contribution guidelines, license |
| T-013 | Create `docs/prompts_book.md` — Prompt Engineering Log | `MED` | `[x]` | Developer | Every significant prompt used logged with context, goal, received output, refinements |

---

## Phase 2 — Project Skeleton (Milestone M2)

> **Goal:** Repository structure, configuration files, and package definition in place.  
> **Exit Criteria:** `uv sync` runs cleanly; all config files present and versioned; secrets in `.env-example` only.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-014 | Initialize `pyproject.toml` with `uv` — name, version, dependencies, ruff/pytest/coverage config | `HIGH` | `[x]` | Developer | `uv sync` succeeds; `[tool.ruff]`, `[tool.coverage]` sections present; no `requirements.txt` |
| T-015 | Create full directory structure per PLAN.md §3 | `HIGH` | `[x]` | Developer | All directories exist: `src/`, `tests/`, `docs/`, `config/`, `data/`, `results/`, `assets/`, `notebooks/` |
| T-016 | Create `__init__.py` files for all packages and sub-packages | `HIGH` | `[x]` | Developer | Every directory under `src/` and `tests/` has `__init__.py`; `__version__` defined in main `__init__.py` |
| T-017 | Create `src/article_generator/shared/version.py` — version tracking | `MED` | `[x]` | Developer | `VERSION = "1.00"` defined; imported by `__init__.py` |
| T-018 | Create `src/article_generator/constants.py` — immutable project constants | `MED` | `[x]` | Developer | All non-configurable constants defined; no configurable values present |
| T-019 | Create `config/setup.json` — main application config (versioned) | `HIGH` | `[x]` | Developer | Matches schema in PLAN.md §7.1; `"version": "1.00"`; all required keys present |
| T-020 | Create `config/rate_limits.json` — API rate limit config (versioned) | `HIGH` | `[x]` | Developer | Matches schema in PLAN.md §7.2; `"version": "1.00"` |
| T-021 | Create `config/model_pricing.json` — LLM token pricing (versioned) | `HIGH` | `[x]` | Developer | Matches schema in PLAN.md §7.13; ≥ 5 models with input/output cost per million; budget thresholds set |
| T-022 | Create `.env-example` — placeholder secrets | `HIGH` | `[x]` | Developer | Contains `LLM_API_KEY=your_key_here` and `SERPER_API_KEY=your_key_here`; no real keys present |
| T-023 | Create `.gitignore` | `HIGH` | `[x]` | Developer | Includes: `.env`, `*.pem`, `*.key`, `credentials.json`, `results/`, `__pycache__/`, `.ruff_cache/`, `uv.lock` (if desired) |
| T-024 | Run `uv lock` to generate `uv.lock` | `HIGH` | `[x]` | Developer | `uv.lock` committed; `uv sync` installs all deps cleanly on clean machine |

---

## Phase 3 — Infrastructure & Core Agents (Milestone M3)

> **Goal:** All CrewAI agents and shared infrastructure implemented with passing unit tests.  
> **Exit Criteria:** `uv run pytest tests/unit/` passes; coverage ≥ 85% on unit scope; zero ruff violations.

### 3A — Shared Infrastructure

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-025 | Implement `shared/config.py` — `ConfigManager` | `HIGH` | `[x]` | Developer | Loads `setup.json`, `rate_limits.json`, `model_pricing.json`; validates version compatibility; raises on missing keys |
| T-026 | Implement `shared/gatekeeper.py` — `ApiGatekeeper` | `HIGH` | `[ ]` | Developer | Rate limiting enforced; FIFO queue on overflow; retry on transient failures; every call logged as `CallRecord` with tokens + timestamp; `get_call_records()` and `get_token_stats()` functional |
| T-027 | Write unit tests for `ConfigManager` (`tests/unit/test_shared/test_config.py`) | `HIGH` | `[ ]` | Developer | Tests: valid config loads, version mismatch raises, missing key raises, defaults applied |
| T-028 | Write unit tests for `ApiGatekeeper` (`tests/unit/test_shared/test_gatekeeper.py`) | `HIGH` | `[ ]` | Developer | Tests: rate limit respected, queue used on overflow, retry on 429, CallRecord logged, token stats accurate; all external calls mocked |

### 3B — Agent Tools

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-029 | Implement `services/tools/search_tools.py` — `SerperDevTool` wrapper and factory | `HIGH` | `[ ]` | Developer | `SerperDevTool` configured with `SERPER_API_KEY` from env; tool factory returns configured instance; raises `EnvironmentError` if key missing |
| T-030 | Write unit tests for `search_tools.py` (`tests/unit/test_tools/test_search_tools.py`) | `HIGH` | `[ ]` | Developer | Tests: tool created with valid key, raises on missing key; external Serper API mocked |

### 3C — Agent Definitions

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-031 | Implement `services/agents/researcher.py` — `ResearcherAgent` | `HIGH` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[SerperDevTool()]`, `skills=["./skills/researcher"]`; role/goal/backstory set |
| T-032 | Implement `services/agents/writer.py` — `WriterAgent` | `HIGH` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[]`, `skills=["./skills/writer"]`; NO internet search tool |
| T-033 | Implement `services/agents/editor.py` — `EditorAgent` (Reviewer/QC) | `HIGH` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[]`, `skills=["./skills/editor"]`; role/goal/backstory set |
| T-034 | Implement `services/agents/graph_generator.py` — `GraphGeneratorAgent` | `MED` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[CodeInterpreterTool()]`, `skills=["./skills/graph_generator"]` |
| T-035 | Implement `services/agents/latex_formatter.py` — `LaTeXFormatterAgent` | `HIGH` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[FileWriterTool()]`, `skills=["./skills/latex_formatter"]` |
| T-036 | Implement `services/agents/bidi_specialist.py` — `BiDiSpecialistAgent` | `HIGH` | `[ ]` | Developer | `build()` returns `crewai.Agent` with `tools=[FileReadTool(), FileWriterTool()]`, `skills=["./skills/bidi_specialist"]` |
| T-037 | Implement `services/tasks/task_definitions.py` — all `Task` objects | `HIGH` | `[ ]` | Developer | 6 tasks defined; each has `description`, `expected_output`, `agent` assignment; context chaining configured |
| T-038 | Implement `services/crew_service.py` — `CrewService` | `HIGH` | `[ ]` | Developer | Builds `crewai.Crew` in Sequential or Hierarchical mode; `run_pipeline()` returns `ArticleResult` |
| T-039 | Write unit tests for all 6 agents (`tests/unit/test_agents/`) | `HIGH` | `[ ]` | Developer | Tests: `build()` returns Agent; correct tools assigned (Researcher→SerperDevTool, GraphGenerator→CodeInterpreterTool, LaTeXFormatter→FileWriterTool, BiDi→FileReadTool+FileWriterTool, Writer/Editor→[]); `skills=` path present for all 6; LLM calls mocked |
| T-040 | Write unit tests for `CrewService` (`tests/unit/test_services/test_crew_service.py`) | `HIGH` | `[ ]` | Developer | Tests: crew assembles correctly, pipeline runs, context passes between agents; all LLM + Serper calls mocked |

---

## Phase 4 — Content Generation Pipeline (Milestone M4)

> **Goal:** Full Markdown article generated by the agent crew, validated by the Reviewer agent.  
> **Exit Criteria:** Running the pipeline produces a valid Markdown file with all mandatory sections.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-041 | Implement `services/file_manager.py` — `FileManager` | `MED` | `[ ]` | Developer | Read/write Markdown, JSON, config; all paths relative; no absolute paths in code |
| T-042 | Implement `sdk/sdk.py` — `ArticleGeneratorSDK` skeleton | `HIGH` | `[ ]` | Developer | All public methods defined; delegates to services; no business logic in SDK itself |
| T-043 | Implement `src/main.py` — CLI entry point | `HIGH` | `[ ]` | Developer | Loads config, instantiates SDK, calls `generate_article()`, prints summary; handles errors gracefully |
| T-044 | Write unit tests for `FileManager` (`tests/unit/test_services/test_file_manager.py`) | `MED` | `[ ]` | Developer | Tests: read/write Markdown, JSON; error on missing file; no real FS calls (mocked) |
| T-045 | Write unit tests for `ArticleGeneratorSDK` (`tests/unit/test_sdk/test_sdk.py`) | `HIGH` | `[ ]` | Developer | Tests: correct delegation to services; method signatures match PLAN.md §6.1 |
| T-046 | End-to-end test: Researcher performs live internet search | `HIGH` | `[ ]` | Developer | Running with a real `SERPER_API_KEY` returns search results; outline includes factual data |
| T-047 | End-to-end test: Full Markdown article generated | `HIGH` | `[ ]` | Developer | Output Markdown contains: abstract, introduction, ≥ 4 chapters, conclusion, bibliography list |

---

## Phase 5 — Visual Elements (Milestone M5)

> **Goal:** Graph generated programmatically, image embedded, table produced, fancy formula present in Markdown.  
> **Exit Criteria:** All 4 visual element types present in the generated Markdown/assets.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-048 | Implement `services/graph_runner.py` — `GraphRunner` | `HIGH` | `[ ]` | Developer | Executes Python graph code safely in subprocess; validates code before execution; saves figure to `assets/`; raises on execution error |
| T-049 | Write unit tests for `GraphRunner` (`tests/unit/test_services/test_graph_runner.py`) | `HIGH` | `[ ]` | Developer | Tests: valid code produces file in assets/, invalid code raises, path returned correctly |
| T-050 | Verify graph code produced by `GraphGeneratorAgent` is executable | `HIGH` | `[ ]` | Developer | Agent output runs without error; produces a `.png` or `.pdf` figure in `assets/` |
| T-051 | Verify at least one image asset is present and embeddable | `MED` | `[ ]` | Developer | `assets/` contains at least one image file; LaTeX `\includegraphics` path is valid |
| T-052 | Verify Writer agent produces at least one Markdown table | `HIGH` | `[ ]` | Developer | Markdown output contains a `| col | col |` table; converts cleanly to LaTeX `tabular` |
| T-053 | Verify LaTeX Formatter agent produces at least one "fancy" formula | `HIGH` | `[ ]` | Developer | `.tex` output contains at least one math environment (`equation`, `align`, etc.) with `\frac`, `\sum`, `\int`, or similar; no plain-text formula approximations |

---

## Phase 6 — LaTeX Pipeline (Milestone M6)

> **Goal:** `.tex` and `.bib` files generated; PDF compiled successfully with zero LaTeX errors.  
> **Exit Criteria:** `results/article.pdf` exists; ≥ 15 pages; all mandatory structural elements present.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-054 | Implement `services/latex_compiler.py` — `LaTeXCompiler.generate_tex()` | `HIGH` | `[ ]` | Developer | Converts Markdown to complete `.tex`; includes: title page, `\tableofcontents`, chapters, `fancyhdr`, `hyperref`, `polyglossia`/`babel` |
| T-055 | Implement `LaTeXCompiler.generate_bib()` | `HIGH` | `[ ]` | Developer | Produces valid `.bib` file from reference list; all entries have required BibTeX fields |
| T-056 | Implement `LaTeXCompiler.compile()` — 4-pass LuaLaTeX + biber | `HIGH` | `[ ]` | Developer | Runs: lualatex → biber → lualatex → lualatex; captures log; raises structured error on failure; returns `CompilationResult` |
| T-057 | Write unit tests for `LaTeXCompiler` (`tests/unit/test_services/test_latex_compiler.py`) | `HIGH` | `[ ]` | Developer | Tests: valid `.tex` generates valid structure, `.bib` output format correct, compilation error captured; subprocess mocked |
| T-058 | Integration test: compile sample `.tex` to PDF | `HIGH` | `[ ]` | Developer | Given a valid `.tex` + `.bib`, `compile()` produces `results/article.pdf` with zero errors |
| T-059 | Verify compiled PDF has cover sheet with all required fields | `HIGH` | `[ ]` | Developer | PDF page 1 contains: topic, author, date, course, lecturer |
| T-060 | Verify PDF table of contents is present and links are clickable | `HIGH` | `[ ]` | Developer | TOC entries present; clicking jumps to correct chapter |
| T-061 | Verify tables in PDF do not overflow page margins | `HIGH` | `[ ]` | Developer | Visual inspection confirms all tables fit within margins; `\resizebox` or `tabularx` used where needed |

---

## Phase 7 — BiDi & Bibliography (Milestone M7)

> **Goal:** Hebrew–English bidirectional text renders correctly; all citations are linked and clickable.  
> **Exit Criteria:** BiDi chapter renders without corruption; clicking any `\cite{}` jumps to bibliography entry.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-062 | Verify `polyglossia` or `babel` configured for Hebrew + English in `.tex` preamble | `HIGH` | `[ ]` | Developer | Preamble contains `\usepackage{polyglossia}` (or `babel`) with Hebrew and English language setup |
| T-063 | Verify at least one chapter has correct RTL ↔ LTR switching | `HIGH` | `[ ]` | Developer | Compiled PDF shows Hebrew text right-aligned, English left-aligned in the same chapter without corruption |
| T-064 | Verify `BiDiSpecialistAgent` fixes any plain-text formula degradation | `HIGH` | `[ ]` | Developer | Agent output contains no `sigma` / `integral` plain-text; all formulas are LaTeX math commands |
| T-065 | Verify `.bib` file contains ≥ 5 references with all required fields | `HIGH` | `[ ]` | Developer | `.bib` file parseable by biber; ≥ 5 entries; each entry has `author`, `title`, `year`, `journal/booktitle` |
| T-066 | Verify all `\cite{key}` commands in `.tex` resolve to `.bib` entries | `HIGH` | `[ ]` | Developer | After 4-pass compilation, no "undefined citation" warnings in LaTeX log |
| T-067 | Verify bibliography appears as final section in PDF | `HIGH` | `[ ]` | Developer | Last section of PDF is bibliography; all entries displayed; clicking in-text citation jumps to entry |

---

## Phase 8 — Cost Tracking (Milestone M8 prerequisite)

> **Goal:** Full token tracking and cost reporting operational.  
> **Exit Criteria:** `cost_report.json` generated on every run; cross-model comparison includes ≥ 3 providers.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-068 | Implement `services/cost_tracker.py` — `CostTracker` | `HIGH` | `[ ]` | Developer | `generate_report()`, `compare_models()`, `check_budget_alert()`, `save_report()` all functional; pricing loaded from `model_pricing.json` |
| T-069 | Wire `CostTracker` into `ArticleGeneratorSDK` | `HIGH` | `[ ]` | Developer | `SDK.get_cost_report()` and `SDK.compare_model_costs()` return populated objects |
| T-070 | Write unit tests for `CostTracker` (`tests/unit/test_services/test_cost_tracker.py`) | `HIGH` | `[ ]` | Developer | Tests: cost calculation accuracy, report format, budget alert fires at threshold, comparison covers ≥ 3 models; ApiGatekeeper mocked |
| T-071 | Verify `cost_report_<timestamp>.json` saved to `results/` after every run | `HIGH` | `[ ]` | Developer | File exists in `results/`; valid JSON; matches `CostReport` schema in PLAN.md §7.12 |
| T-072 | Verify cross-model comparison covers ≥ 3 LLM providers | `MED` | `[ ]` | Developer | Report `cross_model_comparison.entries` has ≥ 3 `ModelCostEntry` items with different `provider` values |
| T-073 | Verify budget alert fires when cost exceeds threshold | `MED` | `[ ]` | Developer | Setting `budget.alert_threshold_usd = 0.01` triggers WARNING log during test run |

---

## Phase 9 — Integration & QA (Milestone M8)

> **Goal:** Full pipeline passes end-to-end; all quality gates met.  
> **Exit Criteria:** All items in Project.md §5 Evaluation Criteria verified; coverage ≥ 85%; zero ruff violations.

| ID | Task | Priority | Status | Owner | Definition of Done |
|----|------|----------|--------|-------|--------------------|
| T-074 | Write integration test: full pipeline end-to-end (`tests/integration/test_pipeline.py`) | `HIGH` | `[ ]` | Developer | Pipeline runs with mocked LLM and Serper calls; all agents fire in order; `ArticleResult` populated |
| T-075 | Write integration test: LaTeX compilation (`tests/integration/test_latex_compilation.py`) | `HIGH` | `[ ]` | Developer | Given sample `.tex` + `.bib`, `compile()` produces valid PDF; zero errors in log |
| T-076 | Run `uv run pytest tests/ --cov=src --cov-report=term-missing` | `HIGH` | `[ ]` | Developer | Coverage report shows ≥ 85% global; no module below 80% |
| T-077 | Run `uv run ruff check src/ tests/` | `HIGH` | `[ ]` | Developer | Zero violations reported |
| T-078 | Verify no file in `src/` exceeds 150 lines of code | `HIGH` | `[ ]` | Developer | `wc -l` or ruff check confirms all files ≤ 150 LOC (excluding blanks and comments) |
| T-079 | Verify no secrets or API keys in any source file | `HIGH` | `[ ]` | Developer | `grep -r "sk-" src/` and `grep -r "SERPER" src/` return no hard-coded values |
| T-080 | **Evaluation criterion check:** All links and citations clickable in PDF | `HIGH` | `[ ]` | Developer | Manual PDF test: TOC links, citation links, cross-references all jump to correct targets |
| T-081 | **Evaluation criterion check:** BiDi text direction correct throughout | `HIGH` | `[ ]` | Developer | Hebrew text renders RTL, English renders LTR; no garbled characters or direction corruption |
| T-082 | **Evaluation criterion check:** No table overflows page margins | `HIGH` | `[ ]` | Developer | Visual inspection of all tables in PDF confirms no content cut off at margins |
| T-083 | **Evaluation criterion check:** All formulas compiled as LaTeX math (not plain text) | `HIGH` | `[ ]` | Developer | All formulas render with proper mathematical typesetting; no formula appears as plain `sigma` or `integral` text |
| T-084 | Full run with real API keys; validate final PDF quality | `HIGH` | `[ ]` | Developer | PDF is ≥ 15 pages; cover sheet complete; all visual elements present; BiDi correct; bibliography linked |
| T-085 | Update `README.md` — final user manual | `HIGH` | `[ ]` | Developer | Installation, `uv sync`, `.env` setup, `uv run python src/main.py`, output locations, config guide |
| T-086 | Update `docs/prompts_book.md` with all prompts used during development | `MED` | `[ ]` | Developer | Every significant LLM prompt logged with context, goal, output quality notes |
| T-087 | Final review: verify all items in Project.md §5 Evaluation Criteria are met | `HIGH` | `[ ]` | Developer | All 4 criteria checked off: links clickable, BiDi correct, tables within margins, formulas compiled |

---

## Summary by Phase

| Phase | Milestone | Tasks | Done | In Progress | Not Started |
|-------|-----------|-------|------|-------------|-------------|
| 1 | M1 — Documentation | T-001 to T-013 + T-011b + T-011c | 15 | 0 | 0 |
| 2 | M2 — Project Skeleton | T-014 to T-024 | 11 | 0 | 0 |
| 3 | M3 — Core Agents | T-025 to T-040 | 0 | 0 | 16 |
| 4 | M4 — Content Pipeline | T-041 to T-047 | 0 | 0 | 7 |
| 5 | M5 — Visual Elements | T-048 to T-053 | 0 | 0 | 6 |
| 6 | M6 — LaTeX Pipeline | T-054 to T-061 | 0 | 0 | 8 |
| 7 | M7 — BiDi & Bibliography | T-062 to T-067 | 0 | 0 | 6 |
| 8 | M8 pre — Cost Tracking | T-068 to T-073 | 0 | 0 | 6 |
| 9 | M8 — Integration & QA | T-074 to T-087 | 0 | 0 | 14 |
| **Total** | | **89 tasks** | **26** | **0** | **63** |

---

## Critical Path

The following tasks form the critical path — delay in any one delays the milestone:

```
T-001 (PRD) → T-002 (PLAN) → T-003 (TODO) → T-004..T-011 (dedicated PRDs)
    → T-014 (pyproject.toml) → T-024 (uv.lock)
    → T-025 (ConfigManager) → T-026 (ApiGatekeeper)
    → T-029 (SerperDevTool) → T-031 (ResearcherAgent)
    → T-037 (TaskDefinitions) → T-038 (CrewService)
    → T-042 (SDK) → T-043 (main.py)
    → T-054 (LaTeXCompiler.generate_tex) → T-056 (compile)
    → T-062 (BiDi preamble) → T-065 (.bib file)
    → T-068 (CostTracker) → T-071 (cost_report.json)
    → T-074 (integration test) → T-076 (coverage) → T-087 (final review)
```
