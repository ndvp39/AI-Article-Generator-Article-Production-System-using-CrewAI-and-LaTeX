# PRD_research_tools.md — Dedicated PRD: SerperDevTool Internet Search
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Why Internet Search for an AI Article Generator?
Large Language Models have a fixed knowledge cutoff — they cannot access events, papers, or data published after their training date. For an academic article generator to produce current, factually grounded content, it needs access to live internet search results. This is the purpose of the `SerperDevTool` in the pipeline.

Without internet search:
- The article is limited to the LLM's parametric memory (potentially outdated).
- Citations may be fabricated ("hallucinated") rather than real, verifiable references.
- Statistical claims and recent research findings cannot be verified.

With `SerperDevTool`:
- The Researcher agent performs real Google searches via the Serper API.
- Results include titles, URLs, snippets, and publication metadata.
- The writer agent receives factual, citable content as context.

### 1.2 Serper API
**Serper** (serper.dev) is a Google Search API provider. It wraps Google's search results and returns them as structured JSON, without requiring a custom web scraper. Key properties:

| Property | Value |
|----------|-------|
| Protocol | HTTPS REST API |
| Auth | API key in `X-API-KEY` header |
| Rate limit (free tier) | 2500 queries/month |
| Rate limit (paid) | Configurable; ~10 req/min typical |
| Response format | JSON with `organic`, `knowledgeGraph`, `answerBox` fields |
| Latency | ~200–800 ms per query |

A Serper search query returns up to 10 organic results per call, each with:
- `title` — page title
- `link` — URL
- `snippet` — 2–3 sentence excerpt
- `date` — publication date (when available)
- `position` — rank in results

### 1.3 CrewAI Tool System
In CrewAI, **tools** are callable objects assigned to agents. An agent with a tool can invoke it during task execution to fetch external information. The tool's output is injected into the agent's reasoning context.

```python
from crewai_tools import SerperDevTool

tool = SerperDevTool()   # reads SERPER_API_KEY from environment
agent = Agent(
    role="...",
    tools=[tool],        # agent can now search the web
)
```

When the agent decides to use the tool, CrewAI calls `tool.run(query)` and appends the result to the agent's context window. The agent then reasons over the search results to produce its output.

### 1.4 Tool Isolation Principle
**Critical rule from Project.md §4:** Only the `ResearcherAgent` MAY have `SerperDevTool`. All other agents MUST have `tools=[]`.

Rationale:
1. **Quality control:** The `WriterAgent` should synthesize from the researcher's output, not conduct its own parallel uncoordinated searches that may return duplicate or conflicting results.
2. **Cost control:** Each search call costs API quota. Limiting search to one agent prevents unbounded search usage.
3. **Reproducibility:** A single agent responsible for all research makes the information-gathering step auditable and controllable.
4. **Pipeline integrity:** The sequential workflow relies on the Writer receiving a curated research summary, not raw search results from multiple agents.

Violation of tool isolation is treated as a critical architectural failure.

### 1.5 Search Strategy for Academic Articles
Effective web search for an academic article requires targeted queries, not single broad queries. The `ResearcherAgent` MUST perform:

| Search Type | Example Query | Purpose |
|------------|--------------|---------|
| Overview | `"[topic] overview 2024"` | Establish current state of the field |
| Key concepts | `"[topic] key concepts techniques"` | Identify main themes to cover |
| Recent advances | `"[topic] recent advances research 2023 2024"` | Find cutting-edge developments |
| Statistics/data | `"[topic] statistics data report"` | Ground claims in verifiable numbers |
| Academic sources | `"[topic] site:arxiv.org OR site:scholar.google.com"` | Find citable academic references |

A minimum of **3 distinct searches** is required per article to ensure adequate coverage.

---

## 2. Requirements

### 2.1 Functional Requirements

**REQ-SRCH-01: Mandatory SerperDevTool for ResearcherAgent**
The `ResearcherAgent` MUST be configured with `SerperDevTool` as its only tool. The agent's `tools` list MUST contain exactly one `SerperDevTool` instance. Configuring the Researcher without this tool is a pipeline failure.

**REQ-SRCH-02: Search Tool Isolation — No Other Agent Has Internet Search**
`SerperDevTool` and any internet search tool MUST be assigned ONLY to `ResearcherAgent`. All other agents MUST NOT have any internet search capability. Non-search tools (file I/O, code execution) are permitted on other agents where needed:
- `WriterAgent` — no internet search tool
- `EditorAgent` — no internet search tool
- `GraphGeneratorAgent` — no internet search tool (`CodeInterpreterTool` is permitted)
- `LaTeXFormatterAgent` — no internet search tool (`FileWriterTool` is permitted)
- `BiDiSpecialistAgent` — no internet search tool (`FileReadTool` + `FileWriterTool` permitted)

Verified by unit tests and `validate_tool_isolation()` at crew startup.

**REQ-SRCH-03: Minimum 3 Searches Per Run**
The `ResearcherAgent` MUST perform at least 3 distinct search queries per article generation run. A single broad search is insufficient for academic-quality research.

**REQ-SRCH-04: Minimum 5 References Gathered**
The research output MUST identify at least 5 distinct, citable references (academic papers, authoritative sources, reports). References MUST include: title, URL or DOI, publication year, and author(s) where available.

**REQ-SRCH-05: SERPER_API_KEY from Environment Only**
The Serper API key MUST be loaded exclusively from the `SERPER_API_KEY` environment variable (via `.env` file). It MUST NOT appear in any source file, config file, or log output. `SerperDevTool` reads this variable automatically; no manual key injection in code.

**REQ-SRCH-06: Missing Key Error**
If `SERPER_API_KEY` is not set in the environment, `search_tools.py` factory function MUST raise `EnvironmentError` with message: `"SERPER_API_KEY environment variable not set. Add it to your .env file."` This check MUST occur at tool instantiation, before any agent is built.

**REQ-SRCH-07: Search Results Passed as Context**
The `ResearcherAgent` output (a structured research summary including all search findings and references) MUST be passed as `context` to the `WriterAgent` task. The writer MUST NOT re-search; it works exclusively from the researcher's output.

**REQ-SRCH-08: SearchResult Data Model**
Each search result captured during the research task MUST be stored as a `SearchResult` object before being included in the research summary passed to the writer.

**REQ-SRCH-09: Rate Limiting via ApiGatekeeper**
All `SerperDevTool.run()` calls MUST pass through `ApiGatekeeper.execute()` using the `"serper"` service profile from `rate_limits.json`. Direct calls bypassing the gatekeeper are forbidden.

**REQ-SRCH-10: Search Logging**
Every search query and its result count MUST be logged at `INFO` level: `"Serper search: query='{query}', results={n}"`. This enables post-run auditing of what was searched.

### 2.2 Non-Functional Requirements

**NFR-SRCH-01:** Each Serper API call MUST complete within 10 seconds; `ApiGatekeeper` timeout applies.  
**NFR-SRCH-02:** `search_tools.py` MUST NOT exceed 150 lines.  
**NFR-SRCH-03:** Tool configuration MUST be fully driven by environment variables — zero hard-coded API endpoints or keys.  
**NFR-SRCH-04:** All Serper API calls in unit tests MUST be mocked — no live network calls in `tests/unit/`.  
**NFR-SRCH-05:** `SERPER_API_KEY` MUST never appear in any log output, even at DEBUG level.

---

## 3. Data Models

### 3.1 `SearchResult`

```python
@dataclass
class SearchResult:
    query:      str          # the search query submitted
    title:      str          # page/article title
    url:        str          # full URL
    snippet:    str          # 2–3 sentence excerpt from search result
    position:   int          # rank in search results (1 = top)
    date:       str = ""     # publication date if available (ISO format)
    source:     str = ""     # domain name extracted from URL
```

### 3.2 `ResearchSummary`

```python
@dataclass
class ResearchSummary:
    topic:           str
    queries_run:     list[str]          # all search queries submitted
    search_results:  list[SearchResult] # all raw results retrieved
    references:      list[Reference]    # ≥ 5 structured Reference objects for .bib
    key_findings:    list[str]          # bullet-point factual findings
    statistics:      list[str]          # specific numbers/data points found
    generated_at:    str                # ISO-8601 UTC timestamp
```

The `ResearchSummary` is serialized to a structured string and passed as the `context` input to `WriterAgent`'s task.

### 3.3 `Reference` (reused from PRD_bibliography.md)

```python
@dataclass
class Reference:
    key:        str    # citation key e.g. "lecun2015deep"
    entry_type: str    # "article" | "book" | "misc" | "inproceedings"
    author:     str
    title:      str
    year:       int
    url:        str = ""
    journal:    str = ""
    booktitle:  str = ""
    publisher:  str = ""
    doi:        str = ""
```

---

## 4. `search_tools.py` Interface

### 4.1 Module Responsibilities
`src/article_generator/services/tools/search_tools.py` is responsible for:
1. Validating `SERPER_API_KEY` exists in environment.
2. Creating a configured `SerperDevTool` instance.
3. Providing a factory function used by `ResearcherAgent`.
4. Nothing else — no business logic, no agent configuration.

### 4.2 `build_search_tool() → SerperDevTool`

```python
def build_search_tool() -> SerperDevTool:
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "SERPER_API_KEY environment variable not set. "
            "Add it to your .env file."
        )
    return SerperDevTool()
```

> `SerperDevTool()` reads `SERPER_API_KEY` from the environment automatically. No need to pass the key explicitly — this keeps the key out of function call arguments and logs.

### 4.3 `validate_tool_isolation(agents: list[BaseAgent]) → None`

```python
# Search tools that are forbidden on non-Researcher agents
SEARCH_TOOLS = {"SerperDevTool", "WebsiteSearchTool", "DuckDuckGoSearchTool"}

def validate_tool_isolation(agents: list[BaseAgent]) -> None:
    for agent in agents:
        if agent.role != "Senior Research Specialist":
            tool_names = {type(t).__name__ for t in agent.tools}
            violations = tool_names & SEARCH_TOOLS
            if violations:
                raise ToolIsolationError(
                    f"Agent '{agent.role}' has internet search tool(s) "
                    f"{violations} — only ResearcherAgent may have search tools."
                )
```

Called during `CrewService` initialization to enforce isolation at startup.
Non-search tools (`FileReadTool`, `FileWriterTool`, `CodeInterpreterTool`) do NOT trigger this check.

---

## 5. Input / Output Contract

### 5.1 `ResearcherAgent` Task I/O

| Field | Detail |
|-------|--------|
| **Input** | `topic: str` — the article topic from `ArticleConfig` |
| **Tool** | `SerperDevTool` — performs ≥ 3 Google searches |
| **Output** | `ResearchSummary` as a structured string |
| **Minimum content** | ≥ 3 search queries run; ≥ 5 references identified; key findings bulleted |

**Task description template:**

```
Research the topic: "{topic}"

You MUST perform at least 3 distinct internet searches using your search tool.
For each search:
1. Record the query and all results
2. Extract factual claims, statistics, and data points
3. Identify citable sources (academic papers, reports, authoritative websites)

Produce a structured research summary containing:
- All search queries run
- At least 5 citable references with: title, URL, author(s), year
- Key findings (bullet points)
- Specific statistics and data points found
- Any conflicting information or caveats noted

Output format: structured text with clearly labeled sections.
Do NOT fabricate citations — only include sources you actually found via search.
```

### 5.2 Context Handoff to WriterAgent

The `ResearcherAgent`'s output is passed to `WriterAgent` via CrewAI's `context` mechanism:

```python
writer_task = Task(
    description="Write a 15-page academic article on {topic}...",
    context=[researcher_task],   # researcher output injected here
    agent=writer_agent,
)
```

The writer receives the full `ResearchSummary` text. It MUST:
- Base all factual claims on the research summary.
- Use only the references listed in the summary for `\cite{}` commands.
- NOT perform independent searches (no `SerperDevTool`).

---

## 6. Security and Privacy

### 6.1 API Key Protection
| Rule | Implementation |
|------|---------------|
| Key never in source code | `build_search_tool()` uses `os.environ.get()` only |
| Key never logged | Logger format string must not include `api_key` variable |
| Key never in config files | `config/setup.json` contains no API keys — only `.env` |
| Key in `.gitignore` | `.env` listed in `.gitignore`; only `.env-example` committed |

### 6.2 Search Query Safety
Search queries are constructed from the article topic string. The topic comes from `ArticleConfig.topic` which comes from user input. The Serper API is called with `query=topic`; no shell execution, no URL construction beyond the Serper SDK.

No sanitization of the topic string is required for the Serper API call (it is a plain HTTPS POST). However, topics MUST NOT contain Serper control characters; the SDK handles encoding.

---

## 7. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Searches per run | ≥ 3 | Count of `SearchResult.query` distinct values |
| References found | ≥ 5 | `len(ResearchSummary.references)` |
| Serper API latency | ≤ 10 s per call | `CallRecord.duration_seconds` |
| Tool isolation violations | 0 | `validate_tool_isolation()` raises |
| API key in logs | 0 occurrences | Log scan for key fragment |
| Hallucinated citations | 0 | Every `\cite{key}` has a corresponding search result URL |

---

## 8. Constraints

1. **Search isolation:** `SerperDevTool` (and any internet search tool) MUST appear in exactly one agent's `tools` list — `ResearcherAgent`. Non-search tools (`FileReadTool`, `FileWriterTool`, `CodeInterpreterTool`) are permitted on other agents. Verified by `validate_tool_isolation()` at crew startup.
2. **Environment variable only:** `SERPER_API_KEY` sourced exclusively from environment. Zero exceptions.
3. **Minimum 3 searches:** The task description MUST instruct the agent to perform ≥ 3 searches. The pipeline MUST verify `len(ResearchSummary.queries_run) >= 3` and raise `InsufficientResearchError` if not.
4. **Minimum 5 references:** Pipeline MUST verify `len(ResearchSummary.references) >= 5` before passing context to WriterAgent.
5. **No fabricated citations:** References MUST come from actual search results. The agent prompt explicitly forbids inventing citations.
6. **Rate limiting:** All Serper calls go through `ApiGatekeeper` with `service="serper"` profile (10 RPM, 100 RPH per `rate_limits.json`).
7. **No direct `requests` calls:** The project MUST use `crewai_tools.SerperDevTool`, not a custom `requests.get()` to the Serper API. The SDK handles auth, encoding, and retries.

---

## 9. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **Direct `requests` to Google Search** | Google's Terms of Service prohibit automated scraping of search results. Serper is a compliant API wrapper. |
| **Bing Search API (Azure)** | Requires Azure account and billing setup; Serper is simpler for a student project. SerperDevTool is the crewai-tools standard. |
| **DuckDuckGo Search (free)** | No official API; rate-limiting is aggressive; no academic source filtering. `crewai_tools` does not have a first-class DuckDuckGo tool. |
| **Pre-seeded static research data** | Defeats the purpose of agent-based research; does not satisfy Project.md §4 "mandatory SerperDevTool." |
| **All agents get SerperDevTool** | Violates tool isolation principle; unpredictable and uncoordinated search behavior; higher API cost; harder to audit. |
| **LLM's parametric memory only (no search)** | Leads to hallucinated or outdated citations; violates Project.md §4 explicit mandate. |

---

## 10. Success Criteria

The research tools system is considered successful when all of the following are true:

- [ ] `build_search_tool()` returns a configured `SerperDevTool` when `SERPER_API_KEY` is set.
- [ ] `build_search_tool()` raises `EnvironmentError` when `SERPER_API_KEY` is missing.
- [ ] `ResearcherAgent` has exactly one tool: `SerperDevTool`. Verified by unit test.
- [ ] All other 5 agents have `tools == []`. Verified by unit test and `validate_tool_isolation()`.
- [ ] A live pipeline run with a valid key produces ≥ 3 logged search queries.
- [ ] Research output contains ≥ 5 `Reference` objects with title, URL, year.
- [ ] All references in the final `.bib` file trace back to actual search result URLs.
- [ ] `SERPER_API_KEY` value never appears in any log file or `results/` output.
- [ ] All Serper calls routed through `ApiGatekeeper` with `service="serper"` profile.
- [ ] `InsufficientResearchError` raised if fewer than 3 searches or fewer than 5 references.

---

## 11. Test Scenarios

### Scenario T-001: Tool created with valid key
**Setup:** `SERPER_API_KEY=test_key_123` in environment  
**Action:** `build_search_tool()`  
**Expected:** Returns `SerperDevTool` instance; no exception raised

### Scenario T-002: Missing key raises EnvironmentError
**Setup:** `SERPER_API_KEY` unset (removed from environment)  
**Action:** `build_search_tool()`  
**Expected:** `EnvironmentError` raised with message containing "SERPER_API_KEY environment variable not set"

### Scenario T-003: ResearcherAgent has SerperDevTool
**Setup:** Build `ResearcherAgent` via `researcher.py`  
**Action:** Inspect `agent.tools`  
**Expected:** `len(agent.tools) == 1`; `type(agent.tools[0]).__name__ == "SerperDevTool"`

### Scenario T-004: WriterAgent has no search tools
**Setup:** Build `WriterAgent` via `writer.py`  
**Action:** Inspect `agent.tools`  
**Expected:** No tool in `agent.tools` is of type `SerperDevTool` or any other search tool; `agent.tools == []` (Writer has no tools at all)

### Scenario T-005: Tool isolation validation catches search tool violation
**Setup:** Manually assign `SerperDevTool` to `WriterAgent.tools`  
**Action:** `validate_tool_isolation([researcher, writer, editor, ...])`  
**Expected:** `ToolIsolationError` raised naming "WriterAgent" as the violating agent; `FileWriterTool` on `LaTeXFormatterAgent` does NOT trigger the error

### Scenario T-006: Insufficient research raises error
**Setup:** Mock `ResearcherAgent` to return only 2 search queries and 3 references  
**Action:** Pipeline attempts to pass research context to `WriterAgent`  
**Expected:** `InsufficientResearchError` raised: "Minimum 3 searches required, got 2" (or references variant)

### Scenario T-007: All Serper calls go through gatekeeper
**Setup:** Instrument `ApiGatekeeper.execute()` with a call counter; run researcher task with mocked Serper  
**Action:** Researcher performs 3 searches  
**Expected:** `gatekeeper.execute()` called exactly 3 times for Serper calls; direct `SerperDevTool.run()` not called outside gatekeeper

### Scenario T-008: API key not in logs
**Setup:** Set `SERPER_API_KEY=secret_test_key_do_not_log`; run researcher with mocked results  
**Action:** Capture all log output at all levels (DEBUG through CRITICAL)  
**Expected:** String "secret_test_key_do_not_log" appears nowhere in log output

### Scenario T-009: Research summary passed as context to writer
**Setup:** Mock Serper to return 3 search results; researcher task runs  
**Action:** Check `writer_task.context` after crew assembly  
**Expected:** `writer_task.context` contains `researcher_task`; writer's LLM prompt includes research summary text in its context window
