#!/usr/bin/env python3
"""Claude Code hook: track tool execution telemetry.

Install as a post-tool hook in .claude/settings.json:
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "command": "python3 .claude/hooks/observability_hook.py"
    }]
  }
}
"""
import asyncio
import json
import sys

from observability_ai import ExecutionRecord, ExecutionTelemetry

telemetry = ExecutionTelemetry()


async def track(event: dict) -> None:
    record = ExecutionRecord(
        model=event.get("tool_name", "unknown"),
        provider="claude-code",
        latency_ms=event.get("duration_ms", 0),
        success=not event.get("error"),
        input_tokens=0,
        output_tokens=0,
    )
    await telemetry.record(record)


def main() -> None:
    event = json.load(sys.stdin)
    asyncio.run(track(event))


if __name__ == "__main__":
    main()
