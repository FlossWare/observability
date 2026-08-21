"""observability-ai -- Lightweight LLM observability toolkit.

Provides in-memory observability, structured logging, execution telemetry,
cost tracking, model feedback, and cross-cutting decorators -- all with
zero required external dependencies.

Nothing activates on import (ADR-0001).  Users must explicitly create
and configure backends.
"""

from __future__ import annotations

from observability_ai.decorators import structured_log, track_execution
from observability_ai.observability import InMemoryObservability
from observability_ai.structured_logging import StructuredLoggingObservability
from observability_ai.telemetry import (
    CostTracker,
    ExecutionTelemetry,
    ModelFeedback,
    PrometheusExporter,
)
from observability_ai.types import ExecutionRecord, FeedbackRecord

__all__ = [
    "CostTracker",
    "ExecutionRecord",
    "ExecutionTelemetry",
    "FeedbackRecord",
    "InMemoryObservability",
    "ModelFeedback",
    "PrometheusExporter",
    "StructuredLoggingObservability",
    "structured_log",
    "track_execution",
]

__version__ = "0.1"
