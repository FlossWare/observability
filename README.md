# observability-ai

Lightweight LLM observability toolkit with zero required external dependencies.

Provides in-memory observability, structured JSON logging with trace-id correlation, execution telemetry, cost tracking by model/provider, model quality feedback, and cross-cutting decorators -- all using Python stdlib only.

## Installation

```bash
pip install git+https://github.com/FlossWare/observability-ai.git
```

With optional Prometheus exporter support:

```bash
pip install "observability-ai[prometheus] @ git+https://github.com/FlossWare/observability-ai.git"
```

## Quickstart

```python
import asyncio
from observability_ai import (
    InMemoryObservability,
    StructuredLoggingObservability,
    ExecutionTelemetry,
    CostTracker,
    ModelFeedback,
    track_execution,
    structured_log,
)

async def main():
    # In-memory metrics, events, and spans
    obs = InMemoryObservability()
    await obs.record_metric("latency_ms", 42.0, labels={"model": "gpt-4o"})
    await obs.log_event("request_complete", level="info")
    span_id = await obs.start_span("inference")
    await obs.end_span(span_id, status="ok")

    # Structured JSON logging with trace correlation
    slo = StructuredLoggingObservability(json_format=True)
    await slo.record_metric("tokens", 150.0)
    await slo.log_event("model_selected", context={"model": "claude-sonnet"})

    # Execution telemetry
    telemetry = ExecutionTelemetry()
    await telemetry.record(
        model="gpt-4o", provider="openai",
        latency_ms=320.0, prompt_tokens=100,
        completion_tokens=50, total_tokens=150, cost=0.003,
    )
    print(f"Avg latency: {telemetry.average_latency():.1f} ms")
    print(f"Total cost:  ${telemetry.total_cost():.4f}")

    # Cost tracking
    costs = CostTracker()
    await costs.add(model="gpt-4o", provider="openai", cost=0.003)
    await costs.add(model="claude-sonnet", provider="anthropic", cost=0.002)
    print(f"Total spend: ${costs.total:.4f}")
    print(f"Top models:  {costs.top_models(2)}")

    # Model feedback
    feedback = ModelFeedback()
    await feedback.rate("gpt-4o", 0.9, task_type="summarization")
    await feedback.rate("claude-sonnet", 0.95, task_type="summarization")
    print(f"Rankings: {feedback.model_rankings()}")

asyncio.run(main())
```

### Decorator Usage

The `@track_execution` and `@structured_log` decorators provide automatic instrumentation with explicit opt-in -- you must pass the backend instance (no global state).

```python
import asyncio
from observability_ai import (
    ExecutionTelemetry,
    StructuredLoggingObservability,
    track_execution,
    structured_log,
)

telemetry = ExecutionTelemetry()
slo = StructuredLoggingObservability(json_format=True)

# Auto-record latency, success/failure for every call
@track_execution(telemetry=telemetry, name="summarize", model="gpt-4o", provider="openai")
async def summarize(text: str) -> str:
    return text[:100] + "..."

# Log function entry/exit with structured JSON
@structured_log(logger=slo, level="INFO")
async def fetch_data(url: str) -> dict:
    return {"url": url, "status": "ok"}

# Stack both decorators
@track_execution(telemetry=telemetry, name="classify", model="claude-sonnet", provider="anthropic")
@structured_log(logger=slo, level="DEBUG")
async def classify(text: str) -> str:
    return "positive"

async def main():
    await summarize("a]long document...")
    await fetch_data("https://example.com")
    await classify("great product")

    print(f"Calls tracked: {len(telemetry.get_records())}")
    print(f"Events logged: {len(slo.get_events())}")

asyncio.run(main())
```

Both decorators work with sync functions too:

```python
@track_execution(telemetry=telemetry, name="parse", model="local", provider="cpu")
def parse_document(path: str) -> dict:
    return {"path": path, "pages": 42}

@structured_log(level="DEBUG")
def compute_hash(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()
```

## API Overview

### InMemoryObservability

List/dict-backed metrics, events, and tracing spans. Ideal for testing and local development.

- `record_metric(name, value, labels=None)` -- record a numeric data point
- `log_event(event, level="info", context=None)` -- emit a structured event
- `start_span(name, parent=None)` / `end_span(span_id, status="ok")` -- tracing
- `get_metrics(name=None)` / `get_events(level=None)` / `get_span(span_id)` -- query

### StructuredLoggingObservability

Same protocol as `InMemoryObservability` but backed by Python's stdlib `logging` with optional JSON formatting and trace-id correlation.

### ExecutionTelemetry

Per-call LLM execution tracking with filtering and aggregation.

- `record(model, provider, latency_ms, ...)` -- store an execution record
- `average_latency(model=None)` / `total_tokens_used(model=None)` / `total_cost(model=None)` / `success_rate(model=None)`

### CostTracker

Aggregate cost accounting by model and provider.

- `add(model, provider, cost)` -- record a cost entry
- `total` / `by_model()` / `by_provider()` / `top_models(n=5)` / `reset()`

### ModelFeedback

Quality rating history per model.

- `rate(model, rating, task_type="", comment="")` -- record a rating (0.0--1.0)
- `average_rating(model=None)` / `model_rankings()` / `get_feedback(model=None, task_type=None)`

### Decorators (ADR-0006)

Cross-cutting decorators for automatic instrumentation.

- `@track_execution(telemetry=..., name="...", model="...", provider="...")` -- auto-record latency, success/failure
- `@structured_log(logger=..., level="INFO")` -- log function entry/exit with structured JSON

### PrometheusExporter (optional)

Requires `prometheus_client`. Exposes Counters, Histograms, and Gauges mirroring in-memory telemetry data.

- `observe_execution(record)` -- push an ExecutionRecord
- `observe_feedback(feedback, avg)` -- update average-rating gauge

## FlossWare Engineering Standards

This package implements the following [FlossWare Engineering Standards](https://github.com/FlossWare/engineering-standards) ADRs:

| ADR | Title | How |
|-----|-------|-----|
| [ADR-0001](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0001.md) | Explicit Opt-In | No global state on import; all backends require explicit instantiation |
| [ADR-0006](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0006.md) | Cross-Cutting Decorators | `@track_execution` and `@structured_log` decorators |
| [ADR-0008](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0008.md) | Free-First | Zero required dependencies; Prometheus is optional |
| [ADR-0009](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0009.md) | Core Principles | Modular, composable, contracts over implementations |
| [ADR-0014](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0014.md) | Token Budget Management | Opt-in token/cost tracking via ExecutionTelemetry and CostTracker |
| [ADR-0017](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0017.md) | Agent-Neutral | No agent-specific code or framework bindings |
| [ADR-0020](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0020.md) | Capability-Protocol Separation | Transport-independent observability via structural subtyping |

See [STANDARDS.md](STANDARDS.md) for detailed compliance notes.

## License

MIT
