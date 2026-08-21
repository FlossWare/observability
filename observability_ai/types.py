"""Shared data types for observability-ai.

Provides lightweight dataclasses used across the observability, structured
logging, and telemetry modules.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ExecutionRecord:
    """A single LLM call execution record."""

    model: str
    provider: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: float = field(default_factory=time.time)
    task_id: str = ""
    success: bool = True
    error: str = ""


@dataclass
class FeedbackRecord:
    """A quality rating for a model's output."""

    model: str
    rating: float  # 0.0 -- 1.0
    task_type: str = ""
    comment: str = ""
    timestamp: float = field(default_factory=time.time)
