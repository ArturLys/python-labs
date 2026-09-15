"""Decorators: timing, call logging with a bounded history of recent operations."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

# Last few decorated calls, oldest dropped automatically: deque(maxlen=...) is O(1) at both ends.
RECENT_CALLS: deque[str] = deque(maxlen=5)


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    """Plain decorator: prints how long one call took."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        print(f"[time] {func.__name__}: {(perf_counter() - start) * 1000:.3f} ms")
        return result

    return wrapper


def log_calls(label: str, show_result: bool = False) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Parametrised decorator: a factory that closes over `label` and returns the real decorator."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = func(*args, **kwargs)
            RECENT_CALLS.append(func.__name__)
            suffix = f" -> {result!r}" if show_result else ""
            print(f"[{label}] {func.__name__}{suffix}")
            return result

        return wrapper

    return decorator
