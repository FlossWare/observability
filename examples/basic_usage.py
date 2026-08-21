#!/usr/bin/env python3
"""Basic observability-ai usage example.

Demonstrates execution telemetry and structured logging
decorators wrapping simulated LLM calls.
"""
import asyncio

from observability_ai import ExecutionTelemetry, CostTracker, track_execution, structured_log


telemetry = ExecutionTelemetry()
costs = CostTracker()


@track_execution(telemetry=telemetry, provider="demo", model="gpt-4o")
@structured_log()
async def call_llm(prompt: str) -> str:
    await asyncio.sleep(0.05)  # simulate latency
    return f"Response to: {prompt}"


async def main() -> None:
    for i in range(5):
        result = await call_llm(f"Question {i + 1}")
        await costs.add(provider="demo", model="gpt-4o", cost=0.002)
        print(f"  [{i + 1}] {result}")

    avg = telemetry.average_latency()
    total = await costs.total_cost()
    print(f"\nMetrics: avg_latency={avg:.1f}ms, total_cost=${total:.4f}")


if __name__ == "__main__":
    print("observability-ai basic usage example")
    print("=" * 40)
    asyncio.run(main())
