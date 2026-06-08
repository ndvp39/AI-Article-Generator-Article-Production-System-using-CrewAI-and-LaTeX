# PRD.md — Product Requirements Document
# AI Article Generator: Academic Article Production System using CrewAI and LaTeX

**Version:** 1.10 — Multi-Process Architecture  
**Date:** 2026-06-08  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Project Overview & Context

### 1.1 Project Name
**AI Article Generator** — Automated Academic Article Production System using CrewAI and LaTeX

### 1.2 Project Description
An automated multi-agent system built with **CrewAI** that orchestrates specialized AI agents to collaboratively research, write, and produce a professional academic article (~15 pages). The final output is a professionally typeset **PDF document** generated via LaTeX (LuaLaTeX/XeLaTeX with MiKTeX), fully supporting Hebrew–English bidirectional (BiDi) text.

**Architecture:** Each of the 6 CrewAI agents runs as an **isolated OS process** (`multiprocessing.Process`). Agents communicate exclusively through typed IPC message queues (`multiprocessing.Queue`). A **GatekeeperRouter** validates and routes every inter-agent message. A **Watchdog** monitors process health and enforces per-agent timeouts, ensuring no process hangs or crashes silently.

The system follows a two-phase workflow:
1. **Content Phase** — agents generate and validate article content in Markdown, each in its own process.
2. **Typesetting Phase** — a dedicated LaTeX agent converts the finalized Markdown to `.tex` files and compiles to PDF.

### 1.3 Context
- **Assignment:** HW3 — AI Agents MSC Course
- **Framework:** CrewAI (multi-agent orchestration)
- **Typesetting Engine:** LuaLaTeX or XeLaTeX via MiKTeX
- **Bibliography Engine:** BibTeX / biber (`.bib` files)
- **Graphics:** TikZ (block diagrams), matplotlib/seaborn (data graphs)

### 1.4 User Problem
Academic writing is time-consuming and labor-intensive. Producing a professionally formatted LaTeX document with proper BiDi support, cross-referenced bibliography, and embedded visual elements requires expertise across multiple domains (research, writing, LaTeX, Python). No single tool automates this entire pipeline.

This system solves the problem by:
- Decomposing the writing task into specialized sub-tasks
- Assigning each sub-task to a purpose-built AI agent (researcher, writer, editor, graph generator, LaTeX formatter, BiDi specialist)
- Producing a publication-quality PDF with full academic structure automatically

### 1.5 Market Analysis
- Growing demand for AI-assisted academic writing tools
- Existing solutions (Jasper, Copy.ai, Writesonic) lack professional LaTeX output and structured multi-agent collaboration
- No existing open-source CrewAI pipeline produces a fully compilable LaTeX PDF with BiDi support
- This system targets academic and research environments requiring structured, typeset documents

### 1.6 Target Audience
- MSC/PhD students requiring automated academic report generation
- Researchers who need structured academic output with LaTeX formatting
- Academic staff evaluating multi-agent AI system capabilities
- Developers exploring CrewAI-based document production pipelines

---

## 2. Goals, KPIs & Acceptance Criteria

### 2.1 Measurable Goals

| Goal | Metric | Target |
|------|--------|--------|
| Process isolation | Each agent runs in a distinct PID | 6 distinct PIDs confirmed by tests |
| Fault detection | Watchdog detects crashed process | Within `WATCHDOG_POLL_INTERVAL_SECONDS` |
| Timeout enforcement | Watchdog terminates hung process | Within configured `AGENT_TIMEOUT_SECONDS` |
| IPC reliability | All inter-agent messages pass GatekeeperRouter validation | 100% of messages validated |
| Document length | Pages in compiled PDF | ≥ 15 pages |
| Visual elements — image | Embedded image present | ≥ 1 |
| Visual elements — graph | Python-generated figure compiled | ≥ 1 |
| Visual elements — table | LaTeX table within margins | ≥ 1 |
| Visual elements — formula | "Fancy" compiled math formula | ≥ 1 |
| BiDi support | Proper RTL/LTR chapter | ≥ 1 chapter |
| Bibliography | Linked, clickable references | ≥ 5 references |
| LaTeX compilation | Successful build, zero errors | 0 LaTeX errors |
| Cross-reference integrity | All citations resolve correctly | 100% |
| Token tracking | Input + output tokens counted per API call | 100% of calls tracked |
| Cost report | USD cost breakdown generated per run | Every run produces report |
| Cross-model cost comparison | Same token usage projected across ≥ 3 LLM providers | ≥ 3 providers in report |

### 2.2 KPIs
- **Process isolation:** All 6 agents confirmed running in distinct PIDs, verified by automated test.
- **Crash detection latency:** Watchdog detects unexpected process death within one poll interval (default ≤ 2 s).
- **Timeout enforcement:** Hung agent process terminated within `AGENT_TIMEOUT_SECONDS[role]` + one poll interval.
- **IPC validation coverage:** 100% of inter-agent messages pass through GatekeeperRouter validation.
- **Pipeline completion time:** ≤ 30 minutes end-to-end
- **LaTeX compilation passes:** ≤ 4 sequential passes (per guidelines)
- **API call success rate:** ≥ 95% (with retry/queue)
- **Content coherence:** Academically structured article with all mandatory sections
- **Link integrity:** All in-text citations clickable and jump to bibliography entry
- **Token cost accuracy:** USD cost computed per call with pricing from config; ≤ 1% rounding error
- **Cost report generation time:** `cost_report.json` produced within 1 second of pipeline completion
- **Budget alert:** Warning fired when projected total cost exceeds configured `alert_threshold_usd`

### 2.3 Acceptance Criteria
1. Each of the 6 agents runs in a distinct OS process with a PID different from the main process — confirmed by `tests/integration/test_process_isolation.py`.
2. `GatekeeperRouter` rejects messages with empty content or invalid sender/recipient pairs, raising `GatekeeperValidationError`.
3. `Watchdog` detects a hung (non-responsive) agent process and terminates it within the configured `AGENT_TIMEOUT_SECONDS`, raising `AgentTimeoutError`.
4. `Watchdog` detects an unexpectedly crashed agent process and records `AgentStatus(status="error")` within one poll interval.
5. Compiled PDF is ≥ 15 pages.
2. Cover sheet present, containing: topic, author name, date, course name, lecturer name.
3. Table of contents auto-generated, functional, and all entries are clickable hyperlinks.
4. All chapters properly formatted with headers (chapter title) and footers (page number).
5. At least one image embedded from the `assets/` folder.
6. At least one Python-generated graph (matplotlib/seaborn) embedded.
7. At least one data table formatted within LaTeX page margins (no table overflow).
8. At least one "fancy" mathematical formula properly compiled with LaTeX math commands (not plain text).
9. At least one chapter demonstrates proper Hebrew–English BiDi rendering (RTL ↔ LTR).
10. Bibliography present with all in-text `\cite{}` commands linked to `.bib` entries.
11. All hyperlinks are functional (TOC entries, citations, cross-references).
12. A `cost_report.json` is automatically saved to `results/` at the end of every run.
13. Cost report includes: total input tokens, total output tokens, total USD cost, per-agent breakdown, and cost comparison across ≥ 3 LLM provider/model combinations.
14. A budget alert warning is logged when projected run cost exceeds the configured `alert_threshold_usd`.

---

## 3. Functional Requirements

### 3.1 Core Features

**FR-01: Multi-Agent Pipeline (CrewAI + Multi-Process)**
- System MUST orchestrate 6 specialized CrewAI agents in a sequential pipeline.
- Each agent MUST run as an **isolated OS process** (`multiprocessing.Process`) — see FR-12.
- Context/results MUST flow between agents exclusively through typed IPC message queues — see FR-13.
- The following **4 agent roles are mandatory** (as defined in Project.md §2):
  1. **Researcher Agent** — conducts research and gathers accurate data and key facts. MUST be connected to an internet search tool (`SerperDevTool`). This connection is **mandatory**.
  2. **Writer Agent** — converts raw research materials into a structured article. MUST NOT have access to any internet search tool; receives context exclusively from the Researcher agent.
  3. **Reviewer / Quality Control Agent** — checks factual accuracy and improves text clarity without changing original meaning.
  4. **LaTeX Generation Agent** — converts the final approved text into valid LaTeX code ready for compilation.
- The system additionally includes: Graph Generator Agent and BiDi Specialist Agent.
- Each agent MUST have a clearly defined `role`, `goal`, `backstory`, and assigned `tools`.
- Pipeline orchestration MUST be driven by `ProcessOrchestrator` with 6 `AgentProcessRunner` instances.

**FR-02: Content Generation in Markdown**
- System MUST first generate all article content in Markdown format.
- Generated Markdown MUST include all mandatory sections: abstract, introduction, chapters (≥ 4), conclusion, bibliography list.
- Content MUST be validated and edited before LaTeX conversion.

**FR-03: Visual Element Generation**
- Graph Generator agent MUST produce executable Python code (matplotlib/seaborn) that generates and saves a figure to `assets/` **programmatically** — static image copy is NOT acceptable.
- System MUST embed at least one image from `assets/`.
- Writer agent MUST produce at least one Markdown table that converts cleanly to a LaTeX `tabular` environment.

**FR-04: Mathematical Formula Generation**
- Writer or LaTeX Formatter agent MUST include at least one advanced LaTeX mathematical formula.
- Formula MUST use LaTeX math commands (e.g., `\frac`, `\sum`, `\int`, `\nabla`, subscripts, superscripts).
- Plain-text approximations of formulas are NOT acceptable.
- If BiDi causes formula degradation, the BiDi Specialist agent MUST request correction.

**FR-05: Hebrew–English BiDi Support**
- LaTeX document MUST use `polyglossia` or `babel` with Hebrew/bidi language support.
- At least one chapter MUST demonstrate controlled direction switching (RTL Hebrew ↔ LTR English).
- LuaLaTeX or XeLaTeX engine MUST be used (pdflatex is NOT permitted).

**FR-06: Bibliography Management**
- System MUST produce a `.bib` file containing all references.
- In-text citations MUST use `\cite{key}` commands linked to `.bib` entries.
- BibTeX or biber MUST be used for bibliography compilation.
- Bibliography MUST appear as the final section of the document.

**FR-07: LaTeX Document Structure**
- Generated `.tex` MUST include: cover/title page, table of contents (`\tableofcontents`), chapter divisions (`\chapter` or `\section`), headers/footers (`fancyhdr`).
- Document MUST use `hyperref` package for all internal links and citations.

**FR-08: LaTeX Compilation Pipeline**
- System MUST compile the `.tex` file using LuaLaTeX or XeLaTeX.
- Compilation MUST be performed ≥ 4 sequential passes to ensure all cross-references and citations resolve.
- Output PDF MUST be saved to `results/`.
- Any LaTeX compilation error MUST be reported and the pipeline MUST NOT silently fail.

**FR-12: Process Isolation**
- Each of the 6 CrewAI agents MUST run as an isolated OS process using `multiprocessing.Process`.
- The CrewAI `Agent` object MUST be instantiated **inside** the subprocess — never pickled and passed across process boundaries.
- Each agent process MUST have a distinct PID different from the main process PID.
- Agent processes MUST be spawned fresh on every `run_pipeline()` call — no process reuse between runs.
- Failure in one agent process MUST NOT directly crash or corrupt other agent processes.

**FR-13: IPC Message Passing**
- All inter-agent communication MUST use typed `AgentMessage` objects placed on `multiprocessing.Queue` instances.
- `AgentMessage` MUST contain: `sender` (str), `recipient` (str), `content` (str), `topic` (str), `message_id` (UUID str), `timestamp` (float), `message_type` (`"input" | "output" | "error"`).
- `AgentStatus` MUST contain: `agent_name` (str), `pid` (int), `status` (`"running" | "done" | "error" | "timeout"`), `started_at` (float), `finished_at` (float | None).
- No shared memory, global variables, or direct method calls MAY be used to pass context between agent processes.
- Each agent process reads from one input `Queue` and writes to one output `Queue`.

**FR-14: GatekeeperRouter**
- A `GatekeeperRouter` daemon thread MUST intercept every `AgentMessage` before it reaches the next agent.
- GatekeeperRouter MUST validate: non-empty `content`, valid `sender`/`recipient` adjacent pair per pipeline order, recognised `message_type`.
- GatekeeperRouter MUST raise `GatekeeperValidationError` on any schema or routing violation.
- GatekeeperRouter MUST log every validated message hop: sender → recipient, content length, message_id.
- GatekeeperRouter MUST route valid messages to the correct next agent's input `Queue`.

**FR-15: Watchdog**
- A `Watchdog` daemon thread MUST monitor all 6 agent `AgentProcessRunner` instances throughout pipeline execution.
- Watchdog MUST poll `process.is_alive()` every `WATCHDOG_POLL_INTERVAL_SECONDS` (default: 2 s, configurable in `constants.py`).
- On **unexpected crash** — process dead before completion: Watchdog MUST record `AgentStatus(status="error")` and signal pipeline failure.
- On **timeout** — agent alive but exceeds `AGENT_TIMEOUT_SECONDS[role]`: Watchdog MUST call `process.terminate()`, record `AgentStatus(status="timeout")`, and raise `AgentTimeoutError`.
- Watchdog MUST expose `get_status(agent_name) -> AgentStatus` and `all_healthy() -> bool`.
- All 6 agent processes MUST be terminated and joined on pipeline completion or failure (no zombie processes).

**FR-09: API Gatekeeper**
- ALL LLM API calls MUST go through the centralized `ApiGatekeeper`.
- Gatekeeper enforces rate limits, queues overflow requests, retries on transient failures, and logs all calls.

**FR-10: Configuration-Driven Parameters**
- Article topic, author name, output paths, LLM model, and rate limits MUST be read from configuration files.
- No configurable values may be hard-coded in source files.

**FR-11: Token Tracking & Cost Analysis**
- The `ApiGatekeeper` MUST record `input_tokens`, `output_tokens`, `model_name`, `agent_name`, and `timestamp` for every LLM API call as a `CallRecord`.
- The `CostTracker` service MUST compute USD cost per call using per-million-token pricing loaded from `config/model_pricing.json`.
- System MUST generate a `CostReport` at the end of every pipeline run, automatically saved to `results/cost_report_<ISO-timestamp>.json`.
- `CostReport` MUST include: total input tokens, total output tokens, total USD cost, per-agent token and cost breakdown, and a cross-model cost comparison table.
- Cross-model comparison MUST cover ≥ 3 LLM provider/model combinations (e.g., Claude Sonnet, Claude Haiku, GPT-4o) using pricing loaded from `config/model_pricing.json`.
- All token pricing values MUST be loaded from `config/model_pricing.json` — never hard-coded in source.
- System MUST log a `WARNING` when projected total cost exceeds `budget.alert_threshold_usd` from config.
- Full cost statistics MUST be accessible at any time via `SDK.get_cost_report()`.

### 3.2 Non-Functional Requirements

**NFR-01: Performance**
- Full pipeline (research → write → format → compile) completes within 30 minutes.
- Graph generation Python script runs within 60 seconds.

**NFR-02: Reliability**
- API failures handled with retry logic (max 3 retries, configurable).
- Queue management prevents API overflow from crashing the pipeline.
- LaTeX compilation errors are caught and reported clearly.

**NFR-03: Security**
- No API keys, tokens, or secrets in source code.
- All secrets loaded via environment variables from `.env`.
- `.env-example` committed with placeholder values.

**NFR-04: Maintainability**
- All source code files ≤ 150 lines of code.
- TDD: test coverage ≥ 85%.
- Zero `ruff check` violations.
- Docstrings on all public functions and classes.

**NFR-05: Portability**
- Runs on Windows, macOS, and Linux.
- Package manager: `uv` only (`pip` FORBIDDEN).
- MiKTeX (with LuaLaTeX and biber) must be installed separately.

**NFR-07: Process Fault Tolerance**
- An agent process crash MUST NOT silently pass — Watchdog MUST detect it within one poll interval.
- A timed-out agent process MUST be terminated before the pipeline blocks indefinitely.
- All 6 agent processes MUST be cleaned up (terminated + joined) on both successful completion and error exit.
- `ProcessOrchestrator` MUST catch all `AgentTimeoutError` and subprocess errors and propagate them as structured `ArticleResult` failures — never silent.

**NFR-08: IPC Reliability**
- All inter-agent messages MUST be typed `AgentMessage` instances — no raw strings or untyped objects on queues.
- `GatekeeperRouter` MUST validate every message before routing; zero messages may bypass validation.
- `multiprocessing.Queue` operations MUST use explicit timeouts (`IPC_QUEUE_TIMEOUT_SECONDS`) — no indefinite blocking queue gets.

**NFR-06: Cost Observability**
- Every LLM API call MUST be logged with input tokens, output tokens, model name, agent name, and ISO timestamp.
- Cost report generation MUST complete within 1 second of pipeline completion.
- Historical cost reports saved to `results/` with ISO timestamp in filename for auditability.
- `CostReport` is included in `ArticleResult` and accessible programmatically via the SDK at any time.

---

## 4. User Stories

| ID | As a… | I want to… | So that… |
|----|-------|------------|----------|
| US-01 | Student | Run the pipeline with a configured topic | I receive a complete, compiled academic PDF |
| US-02 | Student | Configure the article topic and author in a config file | I can reuse the system for any subject |
| US-03 | Researcher | See a bibliography with in-text citation links | I can verify and follow all cited sources |
| US-04 | Student | Get an article with Hebrew–English BiDi | The document demonstrates correct bidirectional text control |
| US-05 | Developer | Monitor per-agent pipeline progress in the terminal | I can debug execution and verify each agent's output |
| US-06 | Developer | Configure rate limits from a JSON file | I can manage API usage and costs without touching source code |
| US-07 | Developer | Run tests with `uv run pytest tests/` | I can verify the pipeline passes quality checks |
| US-08 | Developer | See a token and USD cost breakdown per agent after each run | I can identify which agents are most expensive and optimize them |
| US-09 | Researcher | Compare the cost of running the same pipeline across different LLM providers | I can choose the most cost-effective model for my budget |
| US-10 | Developer | Receive a budget alert when projected cost exceeds a configured threshold | I can prevent unexpected API charges |
| US-11 | Developer | Each agent runs in its own OS process | A crash in one agent cannot corrupt the state of another |
| US-12 | Developer | The Watchdog automatically terminates hung agents | The pipeline never blocks indefinitely on a non-responsive agent |
| US-13 | Developer | All inter-agent messages are validated by the GatekeeperRouter | Malformed or empty agent outputs are caught before they propagate downstream |
| US-14 | Developer | Verify process isolation via an automated test | I can confirm that 6 distinct PIDs are produced without running the full LLM pipeline |

---

## 5. Usage Scenarios

### Scenario 1 — Standard Pipeline Execution
1. User configures `config/setup.json` with topic, author, and LLM model.
2. User runs: `uv run python src/main.py`
3. System loads configuration and initializes the CrewAI Crew (Sequential workflow).
4. **Researcher agent** uses `SerperDevTool` to perform live Google searches, gathers accurate data and key facts, and produces a structured research outline. Output passed as context to the next agent.
5. **Writer agent** receives Researcher's context and generates full Markdown content per chapter, including table and formula placeholders. Has NO internet search access.
6. **Reviewer/QC agent** checks factual accuracy and improves text clarity. Passes refined Markdown as context.
7. **Graph Generator agent** produces Python code for the data figure; system executes it programmatically, saving the figure to `assets/`.
8. **LaTeX Formatter agent** converts validated Markdown to a complete `.tex` file with full preamble, `fancyhdr`, `hyperref`, and math environments.
9. **BiDi Specialist agent** validates Hebrew–English direction and corrects any plain-text formula degradation.
10. System compiles `.tex` → PDF (4 LuaLaTeX + 1 biber passes).
11. Final PDF saved to `results/article.pdf`.

### Scenario 2 — API Rate Limit Recovery
1. Writer agent hits LLM API rate limit mid-generation.
2. `ApiGatekeeper` detects limit, queues the pending request.
3. System waits for the rate window to reset, then drains the queue.
4. Pipeline resumes without content loss.

### Scenario 3 — LaTeX Compilation Error
1. LaTeX Formatter generates malformed `.tex`.
2. Compilation subprocess returns non-zero exit code.
3. System captures the LaTeX log, raises a structured error, and reports it.
4. Developer corrects the formatter and re-runs.

### Scenario 5 — Watchdog Timeout Recovery
1. The WriterAgent process stalls (LLM call hangs, no response within timeout).
2. `Watchdog` polls `process.is_alive()` — returns `True`, but elapsed time exceeds `AGENT_TIMEOUT_SECONDS["Academic Article Writer"]`.
3. `Watchdog` calls `process.terminate()` on the writer process.
4. `Watchdog` records `AgentStatus(status="timeout", agent_name="Academic Article Writer")`.
5. `Watchdog` raises `AgentTimeoutError`.
6. `ProcessOrchestrator` catches the error, terminates all remaining processes, and returns `ArticleResult(success=False)`.
7. Developer receives a clear error message: `AgentTimeoutError: Academic Article Writer exceeded timeout`.

### Scenario 6 — GatekeeperRouter Rejects Malformed Message
1. ResearcherAgent process completes but produces empty output (API error returned empty string).
2. ResearcherAgent writes `AgentMessage(content="", message_type="output")` to its output queue.
3. `GatekeeperRouter` reads the message and validates `content` — empty string detected.
4. `GatekeeperRouter` raises `GatekeeperValidationError("Empty content from Senior Academic Researcher")`.
5. `ProcessOrchestrator` catches the error, terminates all processes, and returns `ArticleResult(success=False)`.
6. Developer receives a clear error message pointing to the researcher's empty output.

### Scenario 4 — Cost Report & Budget Alert
1. Pipeline completes (success or partial failure).
2. `CostTracker` aggregates all `CallRecord` entries from the `ApiGatekeeper` log.
3. USD cost computed per call using `config/model_pricing.json` pricing table.
4. Per-agent breakdown assembled; cross-model comparison table computed for ≥ 3 providers.
5. `CostReport` serialized and saved to `results/cost_report_<ISO-timestamp>.json`.
6. Summary printed to terminal: total input tokens, total output tokens, total USD cost, most expensive agent.
7. If total cost > `budget.alert_threshold_usd`, a `WARNING` log entry is emitted.

---

## 6. Assumptions, Dependencies & Constraints

### 6.1 Assumptions
- LLM API is available with a valid key stored in `.env`. Supported providers: **Anthropic Claude** (`LLM_API_KEY`) and **Google Gemini** (`GEMINI_API_KEY`). The active provider is controlled by `ACTIVE_LLM=claude|gemini`.
- A valid **Serper API key** (`SERPER_API_KEY`) is available in `.env` for the Researcher agent's internet search.
- MiKTeX is installed with LuaLaTeX, biber, and relevant Hebrew/BiDi packages.
- Python 3.10+ and `uv` are installed on the host machine.
- The article topic is configurable; default topic defined in `config/setup.json`.

### 6.2 Dependencies

| Dependency | Minimum Version | Purpose |
|-----------|----------------|---------|
| crewai | ≥ 0.80.0 | Multi-agent orchestration |
| crewai[google-genai] | ≥ 0.80.0 | Gemini LLM support via Google Gen AI |
| crewai-tools | ≥ 0.17.0 | SerperDevTool and other built-in agent tools |
| anthropic | latest | LLM provider (Claude) — used when `ACTIVE_LLM=claude` |
| google-genai | latest | LLM provider (Gemini) — used when `ACTIVE_LLM=gemini` |
| matplotlib | ≥ 3.7.0 | Python graph generation |
| python-dotenv | ≥ 1.0.0 | Environment variable loading |
| MiKTeX | latest | LaTeX compilation (external) |
| LuaLaTeX / XeLaTeX | bundled with MiKTeX | BiDi-capable LaTeX engine |
| biber | bundled with MiKTeX | Bibliography compilation |
| Serper API | external service | Google Search API for Researcher agent (requires `SERPER_API_KEY`) |
| multiprocessing | stdlib (Python ≥ 3.10) | OS-level process isolation for agent processes — no installation required |

### 6.3 Constraints
- LaTeX engine: **LuaLaTeX or XeLaTeX only** (pdflatex does not support Hebrew/BiDi).
- Package manager: **`uv` only** — `pip` is forbidden per guidelines.
- LLM provider: **Claude or Gemini only** — controlled via `ACTIVE_LLM` env var. Only one provider's API key is required at a time.
- File size: **≤ 150 lines of code** per source file.
- Test coverage: **≥ 85%** measured by `pytest --cov`.
- Secrets: **never in source code** — only via `.env`. Required secrets: `LLM_API_KEY`, `SERPER_API_KEY`.
- **Writer Agent tool isolation:** Writer agent MUST NOT be assigned `SerperDevTool` or any other internet search tool.
- **Process isolation:** Every agent MUST run in its own `multiprocessing.Process`; in-memory single-process agent execution is NOT permitted.
- **IPC only:** Inter-agent context MUST flow exclusively through `multiprocessing.Queue` + `AgentMessage`; shared memory or direct function calls between agents are NOT permitted.
- **No zombie processes:** All spawned agent processes MUST be terminated and joined before `run_pipeline()` returns.

### 6.4 Out of Scope
- GUI interface.
- Cloud or containerized deployment.
- Multi-language support beyond Hebrew–English.
- Human-in-the-loop editing after initial generation.
- Support for pdflatex engine.
- Internet search access for any agent other than the Researcher agent.

---

## 7. Timeline & Milestones

| # | Milestone | Key Deliverables | Phase |
|---|-----------|-----------------|-------|
| M1 | Documentation Complete | PRD.md, PLAN.md, TODO.md, dedicated PRDs (incl. PRD_research_tools.md) approved | Phase 1 |
| M2 | Project Skeleton | `pyproject.toml`, `uv.lock`, directory structure, `constants.py`, `.env-example`, `config/model_pricing.json` | Phase 2 |
| M3 | Core Agent Definitions | All CrewAI agents defined with roles/goals/tools; unit tests pass | Phase 3 |
| M3.5 | Multi-Process Architecture | Each agent runs as isolated OS process; GatekeeperRouter, Watchdog, ProcessOrchestrator implemented; process isolation + IPC tests pass | Phase 3.5 |
| M4 | Content Pipeline | Full Markdown article generated by crew; Editor validated output | Phase 4 |
| M5 | Visual Elements | Python graph generated; image embedded; table and formula in Markdown | Phase 5 |
| M6 | LaTeX Pipeline | `.tex` file generated; compilation produces valid PDF | Phase 6 |
| M7 | BiDi & Bibliography | Hebrew–English BiDi validated; `.bib` + citations linked | Phase 7 |
| M8 | Integration & QA | Full end-to-end test; coverage ≥ 85%; zero ruff violations; PDF validated; `cost_report.json` generated and verified | Phase 8 |
