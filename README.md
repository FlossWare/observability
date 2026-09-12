# observability

Reusable observability and execution-telemetry capability for FlossWare.

Provides metrics, structured events, tracing, execution telemetry, cost accounting, and instrumentation decorators.

## Architectural boundary

Observability records what happened. It does **not** decide what should happen next.

- execution evidence belongs to Loom's run/evidence model.
- evaluation owns correctness/quality judgments and reward attribution.
- strategy owns adaptive decision-making.
- model-gateway owns model/provider/resource selection and invocation.
- observability measures these activities and exposes telemetry.

Historical model-ranking/feedback helpers must not become a second adaptive routing system. Quality signals belong in `evaluation` and `strategy`; observability may record them.

```text
Loom / gateway / evaluation / strategy
              |
              v
        observability
              |
              v
        metrics/events/traces
```

## Status

Active supporting capability. Keep it transport-independent, explicit-opt-in, and free of orchestration or policy authority.

## License

MIT
