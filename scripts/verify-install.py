#!/usr/bin/env python3
"""Verify observability-ai installation."""
import asyncio
import sys


def main() -> int:
    try:
        from observability_ai import (
            CostTracker,
            ExecutionRecord,
            ExecutionTelemetry,
            structured_log,
            track_execution,
        )
    except ImportError as e:
        print(f"FAIL: Cannot import observability-ai: {e}")
        print("Install: pip install 'git+https://github.com/FlossWare/observability-ai.git'")
        return 1

    from observability_ai import __version__

    print(f"observability-ai v{__version__} installed successfully.")
    print(f"  ExecutionTelemetry: {ExecutionTelemetry}")
    print(f"  CostTracker:       {CostTracker}")
    print(f"  Decorators:        @track_execution, @structured_log")

    # Smoke test
    telemetry = ExecutionTelemetry()
    record = ExecutionRecord(
        model="test", provider="test",
        latency_ms=100.0, success=True,
        input_tokens=10, output_tokens=20,
    )
    asyncio.run(telemetry.record(record))
    print("  Smoke test:        PASS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
