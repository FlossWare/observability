# observability-ai Integration Guide

Install:
```bash
pip install "git+https://github.com/FlossWare/observability-ai.git"
```

---

## Claude Code

### CLAUDE.md snippet

```markdown
## Observability

This project uses `observability-ai` for LLM call tracking.
Wrap LLM calls with tracking decorators to record latency, cost, and outcomes.

```python
from observability_ai import track_execution, structured_log, ExecutionTelemetry

telemetry = ExecutionTelemetry()

@track_execution(telemetry=telemetry, provider="openai", model="gpt-4o")
async def call_llm(prompt: str) -> str:
    ...
```
```

### Hooks

**Post-tool hook** (`hooks/post-tool-observe.py`):
```python
#!/usr/bin/env python3
"""Claude Code hook: log tool execution metrics."""
import asyncio, json, sys, time
from observability_ai import ExecutionTelemetry, ExecutionRecord

telemetry = ExecutionTelemetry()

event = json.load(sys.stdin)
record = ExecutionRecord(
    model=event.get("tool_name", "unknown"),
    provider="claude-code",
    latency_ms=event.get("duration_ms", 0),
    success=not event.get("error"),
    input_tokens=0,
    output_tokens=0,
)
asyncio.run(telemetry.record(record))
print(json.dumps({"decision": "approve"}))
```

### Skills

Create `.claude/skills/show-metrics.md`:
```markdown
---
name: show-metrics
description: Show LLM call metrics from observability-ai
---

Read the telemetry data and display a summary:
- Total calls, success rate, average latency
- Cost breakdown by provider/model
- Recent errors
```

---

## OpenAI Codex

### AGENTS.md snippet
```markdown
## Observability

Track all LLM calls with `observability-ai`:

```python
from observability_ai import track_execution, ExecutionTelemetry

telemetry = ExecutionTelemetry()

@track_execution(telemetry=telemetry, provider="openai")
async def tool_call(prompt: str) -> str:
    ...
```
```

---

## Cursor

### .cursorrules snippet
```
When making LLM API calls, always track execution with observability-ai:
- @track_execution(telemetry=telemetry, provider="name") for latency/cost tracking
- @structured_log(logger=logger) for structured JSON logging

Import from: from observability_ai import track_execution, structured_log, ExecutionTelemetry
Package: pip install "git+https://github.com/FlossWare/observability-ai.git"
```

---

## Crush

### Configuration
```python
from crush import Agent
from observability_ai import track_execution, ExecutionTelemetry

telemetry = ExecutionTelemetry()

class ObservableAgent(Agent):
    @track_execution(telemetry=telemetry, provider="crush")
    async def call_model(self, prompt: str) -> str:
        return await self.backend.chat(prompt)
```

---

## Generic Python Agent

### asyncio integration
```python
import asyncio
from observability_ai import (
    track_execution, structured_log,
    ExecutionTelemetry, CostTracker, ExecutionRecord,
)

telemetry = ExecutionTelemetry()
costs = CostTracker()

# Decorator approach
@track_execution(telemetry=telemetry, provider="openai", model="gpt-4o")
@structured_log()
async def call_llm(prompt: str) -> str:
    ...

# Programmatic approach
async def call_with_tracking(prompt: str) -> str:
    start = time.monotonic()
    try:
        result = await your_llm_call(prompt)
        elapsed = (time.monotonic() - start) * 1000
        await telemetry.record(ExecutionRecord(
            model="gpt-4o", provider="openai",
            latency_ms=elapsed, success=True,
            input_tokens=len(prompt) // 4,
            output_tokens=len(result) // 4,
        ))
        await costs.add(provider="openai", model="gpt-4o", cost=0.01)
        return result
    except Exception:
        await telemetry.record(ExecutionRecord(
            model="gpt-4o", provider="openai",
            latency_ms=(time.monotonic() - start) * 1000,
            success=False, input_tokens=0, output_tokens=0,
        ))
        raise
```

---

## Cross-Package Integration

### With resilience-ai
```python
from resilience_ai import with_retry, with_circuit_breaker
from observability_ai import track_execution, ExecutionTelemetry

telemetry = ExecutionTelemetry()

@with_retry(max_attempts=3, backoff=1.0)
@with_circuit_breaker(provider="openai", max_failures=5)
@track_execution(telemetry=telemetry, provider="openai")
async def call_llm(prompt: str) -> str:
    ...
```

### With security-ai
```python
from observability_ai import track_execution, ExecutionTelemetry
from security_ai import mask_secrets, audit_logged

telemetry = ExecutionTelemetry()

@track_execution(telemetry=telemetry, provider="openai")
@mask_secrets(patterns=[r'(sk-)[a-zA-Z0-9]+'])
@audit_logged(actor="system", resource="llm")
async def call_llm(prompt: str) -> str:
    ...
```

### With model-router-ai
```python
from observability_ai import track_execution, ExecutionTelemetry, CostTracker
from model_router_ai import CostAware

telemetry = ExecutionTelemetry()
costs = CostTracker()

@track_execution(telemetry=telemetry, provider="router")
async def routed_call(prompt: str) -> str:
    router = CostAware(your_backend, prefer_free=True)
    return await router.chat(prompt)
```
