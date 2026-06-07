# PRD_api_gatekeeper.md — Dedicated PRD: API Gatekeeper & Rate Control
# AI Article Generator

**Version:** 1.00  
**Date:** 2026-06-07  
**Course:** AI Agents — MSC Course, HW3  
**Lecturer:** Dr. Yoram Segal  

---

## 1. Theoretical Background

### 1.1 Why a Centralized API Gatekeeper?
When multiple agents each make independent LLM API calls, three failure modes emerge without centralized control:

1. **Rate limit violations** — LLM providers enforce per-minute and per-hour request limits. Six agents firing simultaneously can instantly exhaust the quota, causing `429 Too Many Requests` errors that crash the pipeline mid-run.
2. **Cost overruns** — Without centralized logging, there is no way to track cumulative token usage or project cost until the bill arrives.
3. **Silent failures** — Transient network errors or temporary provider outages cause agent tasks to fail silently unless a retry mechanism is in place.

The API Gatekeeper is the single chokepoint through which all external API calls pass, solving all three problems in one place. This is mandated by SOFTWARE_PROJECT_GUIDELINES.md §4.1: *"All external API calls MUST go through a centralized gatekeeper."*

### 1.2 Rate Limiting Algorithms

#### Token Bucket Algorithm
The token bucket is the standard rate-limiting algorithm for API clients:
- A "bucket" holds tokens up to a maximum capacity (e.g., 30 tokens = 30 requests/minute).
- Tokens are added at a fixed rate (e.g., 1 token every 2 seconds for 30 RPM).
- Each API call consumes one token.
- If the bucket is empty, the caller must wait until a token is available.

```
capacity = requests_per_minute
refill_rate = capacity / 60.0   # tokens per second

on_request():
    if tokens > 0:
        tokens -= 1
        proceed()
    else:
        enqueue(request)
```

#### Sliding Window Counter
For per-hour limits, a sliding window counter tracks requests in the past 3600 seconds. This is more accurate than a fixed window (which can allow 2× the limit at window boundaries).

### 1.3 Queue Management
When the rate limit is hit, requests MUST be queued rather than rejected. Key properties:

- **FIFO (First-In, First-Out):** Requests are processed in the order they arrived.
- **Maximum depth:** Queue has a configurable maximum to provide backpressure signal.
- **Drain mechanism:** As the rate window resets and tokens become available, queued requests are automatically dequeued and executed.
- **Backpressure:** When the queue is full, new requests receive a `QueueFullError` rather than being silently dropped.

### 1.4 Retry Strategy — Exponential Backoff
Transient failures (network timeouts, `500 Internal Server Error`, `503 Service Unavailable`) should be retried with exponential backoff:

```
delay = base_delay * (2 ^ attempt)  + jitter

attempt 0: wait ~1s
attempt 1: wait ~2s
attempt 2: wait ~4s
attempt 3: fail permanently (raise exception)
```

Jitter (random offset) prevents the "thundering herd" problem where all retrying clients hit the server simultaneously after an outage.

### 1.5 Token Counting and Cost Tracking
Every LLM API response includes token usage metadata (`input_tokens`, `output_tokens`). The Gatekeeper captures these per call as a `CallRecord`, which the `CostTracker` later aggregates. This is the only reliable place in the system where token counts are captured — doing it in the Gatekeeper ensures 100% coverage.

---

## 2. Requirements

### 2.1 Core Functional Requirements

**REQ-GK-01: Single Chokepoint**
All external API calls (LLM calls from all 6 agents) MUST be routed through the `ApiGatekeeper.execute()` method. No agent, service, or module MAY call an external API directly.

**REQ-GK-02: Rate Limit Enforcement**
The Gatekeeper MUST enforce:
- `requests_per_minute` limit using a token bucket
- `requests_per_hour` limit using a sliding window counter
- `concurrent_max` limit using a semaphore

All limits are loaded from `config/rate_limits.json`. Hard-coded values are forbidden.

**REQ-GK-03: FIFO Queue on Overflow**
When any rate limit is reached, the Gatekeeper MUST:
1. Place the pending request in a FIFO queue (not reject it)
2. Return a queued status to the caller
3. Automatically drain the queue as the rate window resets

**REQ-GK-04: Maximum Queue Depth & Backpressure**
- Queue MUST have a configurable `max_queue_depth` (from `rate_limits.json`)
- When queue is full, `execute()` MUST raise `QueueFullError` rather than hanging indefinitely

**REQ-GK-05: Retry on Transient Failures**
On HTTP `429`, `500`, `502`, `503` or network timeout:
- MUST retry up to `max_retries` times (from config)
- MUST use exponential backoff with jitter between retries
- After exhausting retries, MUST raise `ApiCallFailedError` with the last error attached

**REQ-GK-06: Call Logging as CallRecord**
Every completed API call (success or failure) MUST be logged as a `CallRecord` containing:
- `call_id` (UUID)
- `agent_name`
- `model`
- `input_tokens`
- `output_tokens`
- `timestamp` (ISO-8601 UTC)
- `duration_seconds`
- `success` (bool)

**REQ-GK-07: Token Statistics**
`get_token_stats()` MUST return a `TokenStats` object aggregated from all logged `CallRecord` entries, including totals and per-call averages.

**REQ-GK-08: Queue Status Visibility**
`get_queue_status()` MUST return a `QueueStatus` object with current queue depth, requests this minute, requests this hour, rate-limited flag, and seconds until next available slot.

**REQ-GK-09: Configuration Validation at Startup**
On initialization, `ApiGatekeeper.__init__()` MUST validate:
- Config version compatibility
- All required rate limit keys present
- All numeric limits are positive integers

### 2.2 Non-Functional Requirements

**NFR-GK-01:** Thread-safe — shared rate limit counters and queue MUST be protected with locks (`threading.Lock` or `asyncio.Lock`).  
**NFR-GK-02:** No business logic — the Gatekeeper is infrastructure only; it has no knowledge of article content or agent semantics.  
**NFR-GK-03:** File size ≤ 150 lines of code — if the implementation exceeds this, split into `gatekeeper.py` + `gatekeeper_queue.py`.  
**NFR-GK-04:** All config values from `rate_limits.json`; zero hard-coded numeric limits.

---

## 3. Configuration Schema

Loaded from `config/rate_limits.json` (see PLAN.md §7.2):

```json
{
  "rate_limits": {
    "version": "1.00",
    "services": {
      "default": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3,
        "max_queue_depth": 50
      },
      "serper": {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "concurrent_max": 2,
        "retry_after_seconds": 10,
        "max_retries": 2,
        "max_queue_depth": 20
      }
    }
  }
}
```

> Note: A separate `"serper"` service profile allows independent rate limiting for the Serper API (used by `SerperDevTool`).

---

## 4. Input / Output Contract

### 4.1 `ApiGatekeeper.__init__(config: RateLimitConfig)`

| Field | Detail |
|-------|--------|
| **Input** | `config: RateLimitConfig` — loaded from `rate_limits.json` |
| **Output** | Initialized gatekeeper with zeroed counters and empty queue |
| **Raises** | `ConfigVersionError` if version incompatible; `ConfigValidationError` if required keys missing |

### 4.2 `ApiGatekeeper.execute(api_call, *args, **kwargs) → Any`

| Field | Detail |
|-------|--------|
| **Input** | `api_call: Callable` — the external API call to execute |
| **Input** | `*args, **kwargs` — forwarded to `api_call` |
| **Output** | Return value of `api_call` |
| **Side effects** | Appends a `CallRecord` to `self.call_records`; updates rate counters |
| **Raises** | `QueueFullError` if queue at max depth; `ApiCallFailedError` after exhausted retries |

**Internal flow:**
```
execute(api_call, *args, **kwargs):
    1. Acquire concurrency semaphore
    2. Check requests_per_minute → if limit hit: enqueue, wait, retry
    3. Check requests_per_hour  → if limit hit: enqueue, wait, retry
    4. Execute api_call(*args, **kwargs) with retry loop
    5. Extract token usage from response
    6. Create and append CallRecord
    7. Release semaphore
    8. Return response
```

### 4.3 `ApiGatekeeper.get_queue_status() → QueueStatus`

| Field | Detail |
|-------|--------|
| **Input** | None |
| **Output** | `QueueStatus` with current snapshot of queue and rate counters |
| **Thread-safe** | YES — reads under lock |

### 4.4 `ApiGatekeeper.get_call_records() → list[CallRecord]`

| Field | Detail |
|-------|--------|
| **Input** | None |
| **Output** | Shallow copy of `self.call_records` list |
| **Thread-safe** | YES — returns copy to prevent external mutation |

### 4.5 `ApiGatekeeper.get_token_stats() → TokenStats`

| Field | Detail |
|-------|--------|
| **Input** | None |
| **Output** | Aggregated `TokenStats` over all `CallRecord` entries |

---

## 5. Internal State Machine

```
                    ┌──────────────────────────────────────────┐
execute(call) ───→  │  CHECK rate limits                        │
                    │  • requests_per_minute (token bucket)     │
                    │  • requests_per_hour   (sliding window)   │
                    │  • concurrent_max      (semaphore)        │
                    └──────┬───────────────┬──────────────────┘
                           │ OK            │ LIMIT HIT
                           ▼               ▼
                    ┌────────────┐  ┌──────────────────────────┐
                    │  EXECUTE   │  │  QUEUE (FIFO)             │
                    │  api_call  │  │  queue.put(call)          │
                    └──────┬─────┘  │  wait for drain signal   │
                           │        └───────────┬──────────────┘
                     SUCCESS│                   │ DRAINED
                           │        ┌───────────┘
                           ▼        ▼
                    ┌────────────────────────────────────────┐
                    │  LOG CallRecord (tokens, time, status)  │
                    └────────────────────────────────────────┘
                           │
                    FAILURE (transient)
                           ▼
                    ┌────────────────────────────────────────┐
                    │  RETRY (exponential backoff + jitter)   │
                    │  max_retries attempts                   │
                    │  → success: log, return                 │
                    │  → exhausted: raise ApiCallFailedError  │
                    └────────────────────────────────────────┘
```

---

## 6. Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Rate limit compliance | 0 `429` errors from provider | Count of 429s in `CallRecord.success=False` |
| Queue wait time | ≤ 60 seconds per request | `CallRecord.duration_seconds` for queued calls |
| Retry success rate | ≥ 90% on transient failures | `success=True` after retry / total retried |
| Call logging coverage | 100% of calls logged | `len(call_records)` == total calls made |
| Token stat accuracy | ≤ 1% error vs. provider billing | Compare `TokenStats.total_tokens` with provider dashboard |
| Thread safety | Zero race conditions | Concurrent stress test with 10 threads |
| `execute()` overhead | ≤ 50ms above bare API call time | Benchmark with mocked `api_call` |

---

## 7. Constraints

1. **No direct API calls:** Every module that calls an LLM or Serper API MUST do so via `ApiGatekeeper.execute()`. Bypassing the gatekeeper is a critical violation.
2. **Config-only limits:** Rate limit values MUST come from `rate_limits.json`. No numeric literals for limits in source code.
3. **Queue, never drop:** On rate limit, requests MUST be queued. Silent dropping of requests is forbidden.
4. **Thread safety:** All shared state (counters, queue, call_records list) MUST be protected. Race conditions that corrupt token counts are critical bugs.
5. **Retry only on transient errors:** Do NOT retry on `400 Bad Request` or `401 Unauthorized` — these are permanent errors.
6. **File size:** `gatekeeper.py` MUST NOT exceed 150 lines. Split into `gatekeeper_queue.py` if needed.
7. **No business logic:** The Gatekeeper MUST NOT know about agents, articles, or LaTeX. It operates only on `Callable` inputs and `CallRecord` outputs.

---

## 8. Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| **Per-agent rate limiting** | Duplicates logic in every agent file; breaks DRY; cannot enforce global limits across all agents; no unified token log. |
| **No rate limiting (fire-and-retry per call)** | Violates guidelines §4.1; causes cascading 429 errors; no cost visibility. |
| **`tenacity` library for retries only** | Handles retries well but not rate limiting or queuing; would still require custom rate limit logic. |
| **`ratelimit` library** | Decorator-based; cannot centralize logging or queue management. |
| **Async queue (`asyncio.Queue`)** | CrewAI's sequential pipeline is synchronous; async queue adds complexity without benefit in this context. |
| **External rate limiter (Redis)** | Overkill for a single-machine local pipeline; adds infrastructure dependency. |

---

## 9. Success Criteria

The API Gatekeeper is considered successful when all of the following are true:

- [ ] All LLM API calls in the pipeline pass through `ApiGatekeeper.execute()` — verified by code review.
- [ ] Running 40 calls against a 30 RPM limit results in the 31st call being queued, not rejected.
- [ ] A simulated `429` response triggers exponential backoff retry; call eventually succeeds.
- [ ] After `max_retries` failed retries, `ApiCallFailedError` is raised with the original error attached.
- [ ] When queue reaches `max_queue_depth`, `QueueFullError` is raised.
- [ ] Every call produces a `CallRecord` with correct `input_tokens`, `output_tokens`, `agent_name`, `timestamp`.
- [ ] `get_token_stats()` returns totals matching the sum of all `CallRecord` token counts.
- [ ] All shared state access is protected; concurrent stress test with 10 threads produces zero corrupted records.
- [ ] All rate limit values read from `rate_limits.json`; zero hard-coded limits in source.
- [ ] `gatekeeper.py` ≤ 150 lines of code.

---

## 10. Test Scenarios

### Scenario T-001: Rate limit enforced — per-minute
**Setup:** Config `requests_per_minute=5`; mock `api_call` returns instantly  
**Action:** Call `execute()` 6 times in rapid succession  
**Expected:** First 5 calls succeed immediately; 6th call is queued; queued call executes after token bucket refills; all 6 produce `CallRecord`

### Scenario T-002: Queue drains after rate window
**Setup:** Config `requests_per_minute=2`, `max_queue_depth=10`; mock 5 rapid calls  
**Action:** Run 5 calls; observe queue depth; wait for rate window to reset  
**Expected:** Queue depth rises to 3 after first 2 calls; decreases to 0 after drain; all 5 `CallRecord`s logged

### Scenario T-003: Backpressure when queue full
**Setup:** Config `max_queue_depth=3`; 10 simultaneous calls with rate limit of 1 RPM  
**Action:** Call `execute()` 10 times  
**Expected:** First call proceeds; next 3 queued; 5th call raises `QueueFullError`

### Scenario T-004: Retry on transient 429
**Setup:** Mock `api_call` to raise HTTP 429 twice, then succeed on 3rd attempt  
**Action:** Call `execute()` once  
**Expected:** `execute()` retries twice; returns successful result on 3rd attempt; `CallRecord.success=True`; total duration reflects backoff delays

### Scenario T-005: No retry on permanent 400
**Setup:** Mock `api_call` to raise HTTP 400 Bad Request  
**Action:** Call `execute()` once  
**Expected:** `ApiCallFailedError` raised immediately (no retries); `CallRecord.success=False`; `max_retries` not consumed

### Scenario T-006: Token counts captured accurately
**Setup:** Mock `api_call` to return response with `input_tokens=150, output_tokens=300`  
**Action:** Call `execute()` 3 times  
**Expected:** `get_token_stats()` returns `total_input_tokens=450, total_output_tokens=900, calls_count=3`

### Scenario T-007: Thread safety under concurrent load
**Setup:** 10 threads each calling `execute()` 5 times against `requests_per_minute=20`  
**Action:** Run all threads simultaneously  
**Expected:** Total `CallRecord` count == 50; `total_input_tokens` matches sum of individual mock responses; no `AttributeError` or corrupted state

### Scenario T-008: Config validation on init
**Setup:** Pass `rate_limits.json` missing the `requests_per_minute` key  
**Action:** Instantiate `ApiGatekeeper`  
**Expected:** `ConfigValidationError` raised at `__init__` time, before any calls are made
