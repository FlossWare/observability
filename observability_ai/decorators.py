"""Cross-cutting decorators for observability-ai (ADR-0006).

Convenience decorators that automatically instrument functions with
execution tracking and structured logging.  All decorators require
explicit backend instances -- nothing activates on import (ADR-0001).

Decorators
----------
track_execution  -- auto-record latency, success/failure, tokens, cost
structured_log   -- log function entry/exit with structured JSON
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import time
from typing import Any, Callable, TypeVar

from observability_ai.types import ExecutionRecord

F = TypeVar("F", bound=Callable[..., Any])

_logger = logging.getLogger(__name__)


# -- track_execution -------------------------------------------------------


def track_execution(
    *,
    telemetry: Any,
    name: str = "",
    model: str = "unknown",
    provider: str = "unknown",
) -> Callable[[F], F]:
    """Decorator that auto-records execution latency and success/failure.

    Wraps both sync and async functions.  After each call, an
    :class:`~observability_ai.types.ExecutionRecord` is appended to
    *telemetry* via its ``record`` method.

    Parameters
    ----------
    telemetry:
        An :class:`~observability_ai.telemetry.ExecutionTelemetry` instance
        (or any object whose ``record`` method matches the same signature).
        Must be provided explicitly (ADR-0001: no global state).
    name:
        Task identifier stored in the record.  Defaults to the decorated
        function's qualified name.
    model:
        Model name stored in the record.
    provider:
        Provider name stored in the record.

    Example
    -------
    ::

        telemetry = ExecutionTelemetry()

        @track_execution(telemetry=telemetry, name="summarize", model="gpt-4o", provider="openai")
        async def summarize(text: str) -> str:
            ...
    """

    def decorator(fn: F) -> F:
        task_name = name or fn.__qualname__

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                success = True
                error = ""
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    success = False
                    error = str(exc)
                    raise
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    await telemetry.record(
                        model=model,
                        provider=provider,
                        latency_ms=elapsed_ms,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        cost=0.0,
                        task_id=task_name,
                        success=success,
                        error=error,
                    )

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                success = True
                error = ""
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    success = False
                    error = str(exc)
                    raise
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    rec = ExecutionRecord(
                        model=model,
                        provider=provider,
                        latency_ms=elapsed_ms,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        cost=0.0,
                        task_id=task_name,
                        success=success,
                        error=error,
                    )
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(telemetry.record(
                            model=model, provider=provider,
                            latency_ms=elapsed_ms,
                            prompt_tokens=0, completion_tokens=0,
                            total_tokens=0, cost=0.0,
                            task_id=task_name, success=success,
                            error=error,
                        ))
                    except RuntimeError:
                        asyncio.run(telemetry.record(
                            model=model, provider=provider,
                            latency_ms=elapsed_ms,
                            prompt_tokens=0, completion_tokens=0,
                            total_tokens=0, cost=0.0,
                            task_id=task_name, success=success,
                            error=error,
                        ))

            return sync_wrapper  # type: ignore[return-value]

    return decorator


# -- structured_log --------------------------------------------------------


def structured_log(
    *,
    logger: Any | None = None,
    level: str = "INFO",
) -> Callable[[F], F]:
    """Decorator that logs function entry and exit with structured JSON.

    Wraps both sync and async functions.  Entry and exit log records
    include the function name, arguments (repr-truncated), elapsed time,
    and success/failure status.

    Parameters
    ----------
    logger:
        A :class:`~observability_ai.structured_logging.StructuredLoggingObservability`
        instance, a stdlib :class:`logging.Logger`, or ``None``.  When
        ``None``, a module-level stdlib logger is used.  Must be provided
        explicitly for structured observability (ADR-0001).
    level:
        Log level string (e.g. ``"INFO"``, ``"DEBUG"``).

    Example
    -------
    ::

        from observability_ai import StructuredLoggingObservability, structured_log

        slo = StructuredLoggingObservability(json_format=True)

        @structured_log(logger=slo, level="INFO")
        async def fetch_data(url: str) -> dict:
            ...
    """

    def decorator(fn: F) -> F:
        func_name = fn.__qualname__
        log_level = getattr(logging, level.upper(), logging.INFO)

        def _truncated_args(args: tuple, kwargs: dict) -> str:
            parts: list[str] = [repr(a)[:80] for a in args]
            parts.extend(f"{k}={repr(v)[:80]}" for k, v in kwargs.items())
            return ", ".join(parts)

        def _emit(
            message: str,
            *,
            extra: dict,
        ) -> None:
            """Emit a log message to whichever backend was provided."""
            if logger is None:
                _logger.log(log_level, message)
            elif hasattr(logger, "log_event"):
                # StructuredLoggingObservability or InMemoryObservability --
                # fire-and-forget the coroutine if we are in a sync context.
                coro = logger.log_event(
                    message,
                    level=level.lower(),
                    context=extra,
                )
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    asyncio.run(coro)
            elif hasattr(logger, "log"):
                # stdlib logging.Logger
                logger.log(log_level, message, extra={"_structured_extra": extra})

        async def _emit_async(
            message: str,
            *,
            extra: dict,
        ) -> None:
            """Emit a log message, awaiting async backends."""
            if logger is None:
                _logger.log(log_level, message)
            elif hasattr(logger, "log_event"):
                await logger.log_event(
                    message,
                    level=level.lower(),
                    context=extra,
                )
            elif hasattr(logger, "log"):
                logger.log(log_level, message, extra={"_structured_extra": extra})

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                args_str = _truncated_args(args, kwargs)
                await _emit_async(
                    f"ENTER {func_name}({args_str})",
                    extra={"function": func_name, "phase": "entry", "args": args_str},
                )
                start = time.perf_counter()
                success = True
                error = ""
                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as exc:
                    success = False
                    error = str(exc)
                    raise
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    status = "ok" if success else f"error: {error}"
                    await _emit_async(
                        f"EXIT  {func_name} [{elapsed_ms:.1f}ms] {status}",
                        extra={
                            "function": func_name,
                            "phase": "exit",
                            "elapsed_ms": elapsed_ms,
                            "success": success,
                            "error": error,
                        },
                    )

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                args_str = _truncated_args(args, kwargs)
                _emit(
                    f"ENTER {func_name}({args_str})",
                    extra={"function": func_name, "phase": "entry", "args": args_str},
                )
                start = time.perf_counter()
                success = True
                error = ""
                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as exc:
                    success = False
                    error = str(exc)
                    raise
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    status = "ok" if success else f"error: {error}"
                    _emit(
                        f"EXIT  {func_name} [{elapsed_ms:.1f}ms] {status}",
                        extra={
                            "function": func_name,
                            "phase": "exit",
                            "elapsed_ms": elapsed_ms,
                            "success": success,
                            "error": error,
                        },
                    )

            return sync_wrapper  # type: ignore[return-value]

    return decorator
