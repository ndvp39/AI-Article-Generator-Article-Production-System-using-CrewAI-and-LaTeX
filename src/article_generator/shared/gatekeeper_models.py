from __future__ import annotations

from dataclasses import dataclass


class QueueFullError(Exception):
    pass


class ApiCallFailedError(Exception):
    pass


@dataclass
class CallRecord:
    call_id: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: str
    duration_seconds: float
    success: bool


@dataclass
class TokenStats:
    calls_count: int
    total_input_tokens: int
    total_output_tokens: int
    avg_input_tokens: float
    avg_output_tokens: float

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens
