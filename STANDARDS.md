# FlossWare Engineering Standards Compliance

This document records which [FlossWare Engineering Standards](https://github.com/FlossWare/engineering-standards) ADRs this repository implements and how.

## Implemented ADRs

### ADR-0001: Explicit Opt-In

**Link:** [ADR-0001](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0001.md)

Logging, telemetry, and metrics never activate automatically on import. All backends (`InMemoryObservability`, `StructuredLoggingObservability`, `ExecutionTelemetry`, `CostTracker`, `ModelFeedback`) must be explicitly instantiated by the user. No module-level global state is created at import time. Decorators (`@track_execution`, `@structured_log`) require explicit backend instances as parameters.

### ADR-0006: Cross-Cutting Decorators

**Link:** [ADR-0006](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0006.md)

The `observability_ai.decorators` module provides two convenience decorators:

- `@track_execution(telemetry=..., name="my_task")` -- automatically records execution latency, success/failure status, and error details. Works with both sync and async functions.
- `@structured_log(logger=..., level="INFO")` -- logs function entry and exit with structured JSON including function name, arguments, elapsed time, and status. Works with both sync and async functions.

Both decorators require explicit backend instances (consistent with ADR-0001).

### ADR-0008: Free-First

**Link:** [ADR-0008](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0008.md)

Zero required external dependencies. The entire core package runs on Python stdlib only. The `PrometheusExporter` class requires `prometheus_client` but is fully optional -- the import is guarded with `try/except ImportError`, and instantiation raises `ImportError` with a clear message if the library is not installed. The optional dependency is declared in `pyproject.toml` under `[project.optional-dependencies]`.

### ADR-0009: Core Principles

**Link:** [ADR-0009](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0009.md)

- **Modular:** Each concern (in-memory observability, structured logging, telemetry, cost tracking, feedback) lives in its own module.
- **Composable:** Backends can be mixed, stacked, or replaced independently. Decorators accept any duck-typed backend.
- **Contracts over implementations:** All backends satisfy the `ObservabilityBackend` protocol via structural subtyping (duck typing) -- no base class inheritance required.

### ADR-0014: Token Budget Management

**Link:** [ADR-0014](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0014.md)

The `ExecutionTelemetry` class tracks per-call token counts (prompt, completion, total) and costs. The `CostTracker` provides aggregate cost accounting by model and provider with `top_models()` for budget awareness. All tracking is opt-in: users must explicitly create instances and call `record()` or `add()` to register usage. No automatic token interception occurs.

### ADR-0017: Agent-Neutral

**Link:** [ADR-0017](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0017.md)

The package contains no agent-specific code, framework bindings, or runtime assumptions. It works with any agent runtime, orchestration framework, or standalone script. All backends use plain Python async/sync interfaces that any caller can drive.

### ADR-0020: Capability-Protocol Separation

**Link:** [ADR-0020](https://github.com/FlossWare/engineering-standards/blob/main/adr/ADR-0020.md)

Observability capabilities are transport-independent. The `ObservabilityBackend` protocol defines the interface (metrics, events, spans) without prescribing how data is stored or transmitted. Implementations range from in-memory lists (`InMemoryObservability`) to stdlib logging (`StructuredLoggingObservability`) to Prometheus (`PrometheusExporter`). Users can implement their own backends by matching the protocol's method signatures.
