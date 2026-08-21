"""Tests for the observability-ai package."""

from __future__ import annotations

import asyncio
import pytest

from observability_ai import (
    CostTracker,
    ExecutionRecord,
    ExecutionTelemetry,
    FeedbackRecord,
    InMemoryObservability,
    ModelFeedback,
    StructuredLoggingObservability,
    structured_log,
    track_execution,
)


# -- InMemoryObservability ------------------------------------------------


@pytest.mark.asyncio
async def test_inmemory_record_metric():
    obs = InMemoryObservability()
    await obs.record_metric("latency", 42.5, labels={"env": "test"})
    metrics = obs.get_metrics("latency")
    assert len(metrics) == 1
    assert metrics[0]["value"] == 42.5
    assert metrics[0]["labels"] == {"env": "test"}


@pytest.mark.asyncio
async def test_inmemory_log_event():
    obs = InMemoryObservability()
    await obs.log_event("started", level="info", context={"step": 1})
    await obs.log_event("failed", level="error")
    assert len(obs.get_events()) == 2
    assert len(obs.get_events(level="error")) == 1
    assert obs.get_events(level="error")[0]["event"] == "failed"


@pytest.mark.asyncio
async def test_inmemory_spans():
    obs = InMemoryObservability()
    span_id = await obs.start_span("inference")
    assert obs.get_span(span_id) is not None
    assert obs.get_span(span_id)["end_time"] is None

    await obs.end_span(span_id, status="ok")
    assert obs.get_span(span_id)["status"] == "ok"
    assert obs.get_span(span_id)["end_time"] is not None


@pytest.mark.asyncio
async def test_inmemory_end_unknown_span_raises():
    obs = InMemoryObservability()
    with pytest.raises(KeyError, match="Unknown span id"):
        await obs.end_span("nonexistent")


# -- StructuredLoggingObservability ---------------------------------------


@pytest.mark.asyncio
async def test_structured_logging_trace_id():
    slo = StructuredLoggingObservability(trace_id="abc123")
    assert slo.trace_id == "abc123"
    await slo.record_metric("tokens", 100.0)
    metrics = slo.get_metrics()
    assert len(metrics) == 1
    assert metrics[0]["trace_id"] == "abc123"


@pytest.mark.asyncio
async def test_structured_logging_spans():
    slo = StructuredLoggingObservability()
    span_id = await slo.start_span("parent_span")
    child_id = await slo.start_span("child_span", parent=span_id)
    await slo.end_span(child_id, status="ok")
    await slo.end_span(span_id, status="ok")

    parent = slo.get_span(span_id)
    child = slo.get_span(child_id)
    assert parent is not None
    assert child is not None
    assert child["parent"] == span_id
    assert parent["status"] == "ok"
    assert child["status"] == "ok"


# -- ExecutionTelemetry ---------------------------------------------------


@pytest.mark.asyncio
async def test_execution_telemetry_record_and_query():
    telemetry = ExecutionTelemetry()
    rec = await telemetry.record(
        model="gpt-4o",
        provider="openai",
        latency_ms=200.0,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost=0.003,
        task_id="task-1",
    )
    assert isinstance(rec, ExecutionRecord)
    assert rec.model == "gpt-4o"

    recs = telemetry.get_records(model="gpt-4o")
    assert len(recs) == 1
    assert telemetry.get_records(model="claude") == []


@pytest.mark.asyncio
async def test_execution_telemetry_aggregations():
    telemetry = ExecutionTelemetry()
    await telemetry.record(
        model="m1", provider="p1",
        latency_ms=100.0, prompt_tokens=50,
        completion_tokens=30, total_tokens=80, cost=0.001,
    )
    await telemetry.record(
        model="m1", provider="p1",
        latency_ms=200.0, prompt_tokens=60,
        completion_tokens=40, total_tokens=100, cost=0.002,
        success=False, error="timeout",
    )
    assert telemetry.average_latency(model="m1") == 150.0
    assert telemetry.total_tokens_used(model="m1") == 180
    assert abs(telemetry.total_cost(model="m1") - 0.003) < 1e-9
    assert telemetry.success_rate(model="m1") == 0.5


# -- CostTracker ----------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_tracker():
    ct = CostTracker()
    await ct.add(model="gpt-4o", provider="openai", cost=0.01)
    await ct.add(model="claude", provider="anthropic", cost=0.02)
    await ct.add(model="gpt-4o", provider="openai", cost=0.005)

    assert abs(ct.total - 0.035) < 1e-9
    assert ct.by_model()["gpt-4o"] == pytest.approx(0.015)
    assert ct.by_provider()["anthropic"] == pytest.approx(0.02)
    assert ct.top_models(1) == [("claude", 0.02)]

    ct.reset()
    assert ct.total == 0.0
    assert ct.by_model() == {}


# -- ModelFeedback --------------------------------------------------------


@pytest.mark.asyncio
async def test_model_feedback():
    fb = ModelFeedback()
    await fb.rate("gpt-4o", 0.9, task_type="summary")
    await fb.rate("gpt-4o", 0.8, task_type="code")
    await fb.rate("claude", 0.95, task_type="summary")

    assert fb.average_rating(model="gpt-4o") == pytest.approx(0.85)
    assert len(fb.get_feedback(task_type="summary")) == 2

    rankings = fb.model_rankings()
    assert rankings[0][0] == "claude"  # highest rated


@pytest.mark.asyncio
async def test_model_feedback_invalid_rating():
    fb = ModelFeedback()
    with pytest.raises(ValueError, match="rating must be in"):
        await fb.rate("model", 1.5)


# -- Types ----------------------------------------------------------------


def test_execution_record_defaults():
    rec = ExecutionRecord(
        model="m", provider="p",
        latency_ms=1.0, prompt_tokens=1,
        completion_tokens=1, total_tokens=2, cost=0.0,
    )
    assert rec.success is True
    assert rec.error == ""
    assert rec.task_id == ""
    assert rec.timestamp > 0


def test_feedback_record_defaults():
    rec = FeedbackRecord(model="m", rating=0.5)
    assert rec.task_type == ""
    assert rec.comment == ""
    assert rec.timestamp > 0


# -- Decorators -----------------------------------------------------------


@pytest.mark.asyncio
async def test_track_execution_async_success():
    telemetry = ExecutionTelemetry()

    @track_execution(telemetry=telemetry, name="my_task", model="gpt-4o", provider="openai")
    async def do_work() -> str:
        return "done"

    result = await do_work()
    assert result == "done"

    recs = telemetry.get_records()
    assert len(recs) == 1
    assert recs[0].task_id == "my_task"
    assert recs[0].model == "gpt-4o"
    assert recs[0].provider == "openai"
    assert recs[0].success is True
    assert recs[0].latency_ms > 0


@pytest.mark.asyncio
async def test_track_execution_async_failure():
    telemetry = ExecutionTelemetry()

    @track_execution(telemetry=telemetry, name="failing_task", model="m", provider="p")
    async def fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await fail()

    recs = telemetry.get_records()
    assert len(recs) == 1
    assert recs[0].success is False
    assert recs[0].error == "boom"


def test_track_execution_sync():
    telemetry = ExecutionTelemetry()

    @track_execution(telemetry=telemetry, name="sync_task", model="local", provider="cpu")
    def compute(x: int) -> int:
        return x * 2

    assert compute(5) == 10

    recs = telemetry.get_records()
    assert len(recs) == 1
    assert recs[0].task_id == "sync_task"
    assert recs[0].success is True
    assert recs[0].latency_ms > 0


def test_track_execution_sync_failure():
    telemetry = ExecutionTelemetry()

    @track_execution(telemetry=telemetry, name="sync_fail", model="m", provider="p")
    def blow_up() -> None:
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        blow_up()

    recs = telemetry.get_records()
    assert len(recs) == 1
    assert recs[0].success is False
    assert recs[0].error == "kaboom"


@pytest.mark.asyncio
async def test_structured_log_async():
    slo = StructuredLoggingObservability()

    @structured_log(logger=slo, level="INFO")
    async def greet(name: str) -> str:
        return f"hello {name}"

    result = await greet("world")
    assert result == "hello world"

    events = slo.get_events()
    assert len(events) == 2  # entry + exit
    assert any("ENTER" in e["event"] for e in events)
    assert any("EXIT" in e["event"] for e in events)


@pytest.mark.asyncio
async def test_structured_log_async_failure():
    slo = StructuredLoggingObservability()

    @structured_log(logger=slo, level="INFO")
    async def fail() -> None:
        raise RuntimeError("oops")

    with pytest.raises(RuntimeError, match="oops"):
        await fail()

    events = slo.get_events()
    assert len(events) == 2
    exit_event = [e for e in events if "EXIT" in e["event"]][0]
    assert "error" in exit_event["event"].lower() or "oops" in exit_event["context"].get("error", "")


@pytest.mark.asyncio
async def test_track_execution_default_name():
    """When name is not provided, the function's qualname is used."""
    telemetry = ExecutionTelemetry()

    @track_execution(telemetry=telemetry, model="m", provider="p")
    async def my_special_function() -> None:
        pass

    await my_special_function()

    recs = telemetry.get_records()
    assert len(recs) == 1
    assert "my_special_function" in recs[0].task_id


@pytest.mark.asyncio
async def test_stacked_decorators():
    """Both decorators can be stacked on the same function."""
    telemetry = ExecutionTelemetry()
    slo = StructuredLoggingObservability()

    @track_execution(telemetry=telemetry, name="stacked", model="m", provider="p")
    @structured_log(logger=slo, level="DEBUG")
    async def combined(x: int) -> int:
        return x + 1

    result = await combined(10)
    assert result == 11
    assert len(telemetry.get_records()) == 1
    assert len(slo.get_events()) == 2  # entry + exit


# -- ADR-0001: No global state on import ---------------------------------


def test_no_global_state_on_import():
    """Importing the package must not create any loggers, trackers, or state."""
    import importlib
    import observability_ai as pkg

    # The module should not have any instantiated backends
    for attr_name in dir(pkg):
        attr = getattr(pkg, attr_name)
        assert not isinstance(attr, (
            InMemoryObservability,
            StructuredLoggingObservability,
            ExecutionTelemetry,
            CostTracker,
            ModelFeedback,
        )), f"Global instance found: {attr_name}"


# -- Zero loom_ai imports -------------------------------------------------


def test_no_loom_ai_references():
    """Verify the package has no loom_ai imports."""
    import inspect
    import observability_ai
    import observability_ai.decorators
    import observability_ai.observability
    import observability_ai.structured_logging
    import observability_ai.telemetry
    import observability_ai.types

    modules = [
        observability_ai,
        observability_ai.decorators,
        observability_ai.observability,
        observability_ai.structured_logging,
        observability_ai.telemetry,
        observability_ai.types,
    ]
    for mod in modules:
        source = inspect.getsource(mod)
        assert "from loom_ai" not in source, f"loom_ai import found in {mod.__name__}"
        assert "import loom_ai" not in source, f"loom_ai import found in {mod.__name__}"
