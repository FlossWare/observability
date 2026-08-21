#!/bin/bash
# Add observability-ai integration to your CLAUDE.md
set -e

CLAUDE_MD="${CLAUDE_MD:-./CLAUDE.md}"

if [ ! -f "$CLAUDE_MD" ]; then
    echo "Creating $CLAUDE_MD..."
    touch "$CLAUDE_MD"
fi

cat >> "$CLAUDE_MD" << 'BLOCK'

## Observability (observability-ai)

This project uses [observability-ai](https://github.com/FlossWare/observability-ai) for LLM call tracking.

**Track all LLM calls with execution telemetry:**

```python
from observability_ai import track_execution, structured_log, ExecutionTelemetry

telemetry = ExecutionTelemetry()

@track_execution(telemetry=telemetry, provider="openai", model="gpt-4o")
@structured_log()
async def call_llm(prompt: str) -> str:
    ...
```

Install: `pip install "git+https://github.com/FlossWare/observability-ai.git"`
BLOCK

echo "Added observability-ai section to $CLAUDE_MD"
