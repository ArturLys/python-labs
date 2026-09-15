"""Measuring tools: timeit-based repeats, cProfile top functions, tracemalloc peak memory."""

from __future__ import annotations

import cProfile
import io
import pstats
import timeit
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Timing:
    label: str
    best: float
    mean: float
    runs: tuple[float, ...]

    def speedup(self, baseline: Timing) -> float:
        return baseline.best / self.best


def measure(label: str, func: Callable[[], object], *, repeats: int = 5, number: int = 1) -> Timing:
    """timeit.repeat: `repeats` independent runs of `number` calls; the best run is the least disturbed one."""
    runs = tuple(t / number for t in timeit.repeat(func, number=number, repeat=repeats))
    return Timing(label, min(runs), sum(runs) / len(runs), runs)


def profile_top(func: Callable[[], object], limit: int = 8) -> str:
    """cProfile the call and return the `limit` most expensive functions by tottime (own time)."""
    profiler = cProfile.Profile()
    profiler.runcall(func)
    buffer = io.StringIO()
    stats = pstats.Stats(profiler, stream=buffer)
    stats.strip_dirs().sort_stats("tottime").print_stats(limit)
    lines = buffer.getvalue().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("ncalls"))
    return "\n".join(line.rstrip() for line in lines[start - 2 : start + 1 + limit] if line.strip())


def peak_memory(func: Callable[[], T]) -> tuple[T, int]:
    """Run under tracemalloc; return (result, peak bytes allocated during the call)."""
    tracemalloc.start()
    try:
        result = func()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


def fmt_bytes(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
