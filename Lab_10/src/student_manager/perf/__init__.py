"""Profiling and optimisation experiments: loops vs threads vs processes vs NumPy, caching (ЛР9)."""

from student_manager.perf.baseline import Stats, compute_stats, stats_close
from student_manager.perf.cache import GroupStatisticsService
from student_manager.perf.dataset import make_students
from student_manager.perf.parallel import race, stats_processes, stats_raw_threads, stats_threads
from student_manager.perf.profiling import Timing, measure, peak_memory, profile_top
from student_manager.perf.vectorized import compute_stats_numpy, compute_stats_numpy_from_students, to_arrays

__all__ = [
    "GroupStatisticsService",
    "Stats",
    "Timing",
    "compute_stats",
    "compute_stats_numpy",
    "compute_stats_numpy_from_students",
    "make_students",
    "measure",
    "peak_memory",
    "profile_top",
    "race",
    "stats_close",
    "stats_processes",
    "stats_raw_threads",
    "stats_threads",
    "to_arrays",
]
