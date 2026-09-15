"""``python -m student_manager.perf [--size N] [--repeats R]`` — the whole experiment, results also to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from time import perf_counter

import numpy as np

from student_manager.perf import (
    GroupStatisticsService, Stats, Timing, compute_stats, compute_stats_numpy, compute_stats_numpy_from_students,
    make_students, measure, peak_memory, profile_top, race, stats_close, stats_processes, stats_raw_threads,
    stats_threads, to_arrays,
)
from student_manager.perf.parallel import stats_processes_columns, to_columns
from student_manager.perf.profiling import fmt_bytes


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def table(timings: list[Timing], baseline: Timing) -> None:
    print(f"  {'метод':<34}{'best, s':>10}{'mean, s':>10}{'speedup':>9}")
    for t in timings:
        print(f"  {t.label:<34}{t.best:>10.4f}{t.mean:>10.4f}{t.speedup(baseline):>8.2f}×")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m student_manager.perf")
    parser.add_argument("--size", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--csv", type=Path, default=Path("data/benchmark.csv"))
    args = parser.parse_args(argv)
    rows: list[dict[str, object]] = []

    show(f"Тестовий набір: {args.size:,} студентів, 20 груп, оцінки 40..100 (seed 42)".replace(",", " "))
    start = perf_counter()
    students = make_students(args.size)
    print(f"  згенеровано за {perf_counter() - start:.2f} s; перший: {students[0]}")
    print(f"  Python: {sys.version.split()[0]}, CPU: {__import__('os').cpu_count()} логічних ядер")

    show("Baseline (Python loops): результат і правильність")
    base = compute_stats(students)
    print(f"  count={base.count} mean={base.mean:.4f} min={base.minimum} max={base.maximum} std={base.std:.4f}")
    print("  group_means (перші 3):", {k: round(v, 3) for k, v in list(base.group_means.items())[:3]})
    print("  top-3 ranking:", [(students[i].full_name, students[i].average_grade) for i in base.ranking[:3]])
    check = np.array([s.average_grade for s in students])
    print(f"  контроль через statistics/NumPy: mean={check.mean():.4f} std={check.std():.4f} -> збігається: "
          f"{abs(check.mean() - base.mean) < 1e-9 and abs(check.std() - base.std) < 1e-7}")

    show(f"timeit baseline: {args.repeats} повторів")
    t_base = measure("Python loops (baseline)", partial(compute_stats, students), repeats=args.repeats)
    print("  runs:", [f"{r:.4f}" for r in t_base.runs], f"best={t_base.best:.4f} s mean={t_base.mean:.4f} s")

    show("cProfile baseline (top за tottime)")
    print(profile_top(partial(compute_stats, students)))

    show("tracemalloc: peak memory")
    _, peak_base = peak_memory(partial(compute_stats, students))
    _, peak_arrays = peak_memory(partial(to_arrays, students))
    arrays = to_arrays(students)
    _, peak_numpy = peak_memory(partial(compute_stats_numpy, arrays))
    list_bytes = sys.getsizeof(students) + sum(sys.getsizeof(s) for s in students[:1000]) * (len(students) / 1000)
    print(f"  baseline compute_stats: peak {fmt_bytes(peak_base)}")
    print(f"  to_arrays (list -> ndarray): peak {fmt_bytes(peak_arrays)}; масиви: {fmt_bytes(arrays.grades.nbytes + arrays.group_ids.nbytes)}")
    print(f"  compute_stats_numpy: peak {fmt_bytes(peak_numpy)}")
    print(f"  list[Student] (оцінка, без рядків): {fmt_bytes(list_bytes)} проти ndarray grades {fmt_bytes(arrays.grades.nbytes)}")
    print("  висновок: операція CPU-bound — жодного I/O, час іде на байткод циклу та sorted")

    show("Правильність усіх реалізацій відносно baseline")
    implementations: dict[str, Stats] = {
        "threads x4": stats_threads(students, 4),
        "raw threads + Lock x4": stats_raw_threads(students, 4),
        "processes x4": stats_processes(students, 4),
        "numpy": compute_stats_numpy_from_students(students),
    }
    for name, result in implementations.items():
        print(f"  {name:<24} збігається: {stats_close(base, result)}")

    show(f"Benchmark ({args.repeats} повторів, best/mean), speedup = baseline.best / best")
    columns = to_columns(students)
    print(f"  to_columns (об'єкти -> списки float/int): {measure('c', partial(to_columns, students), repeats=3).best:.4f} s")
    timings = [t_base]
    for workers in (1, 2, 4, 8):
        timings.append(measure(f"ThreadPoolExecutor x{workers}", partial(stats_threads, students, workers), repeats=args.repeats))
    timings.append(measure("ProcessPool x4, об'єкти, новий пул", partial(stats_processes, students, 4), repeats=args.repeats))
    timings.append(measure("ProcessPool x4, колонки, новий пул", partial(stats_processes_columns, columns, 4), repeats=args.repeats))
    with ProcessPoolExecutor(max_workers=8) as warm:
        stats_processes_columns(columns, 8, warm)  # spawn the workers once, outside the measurement
        for workers in (1, 2, 4, 8):
            timings.append(measure(f"ProcessPool x{workers}, колонки, теплий пул",
                                   partial(stats_processes_columns, columns, workers, warm), repeats=args.repeats))
    timings.append(measure("NumPy (з конвертацією)", partial(compute_stats_numpy_from_students, students), repeats=args.repeats))
    timings.append(measure("NumPy (масиви готові)", partial(compute_stats_numpy, arrays), repeats=args.repeats))
    table(timings, t_base)
    rows += [{"size": args.size, "method": t.label, "best": round(t.best, 5), "mean": round(t.mean, 5),
              "speedup": round(t.speedup(t_base), 3)} for t in timings]

    show("Різні розміри даних: baseline / NumPy (з конвертацією) / теплий ProcessPool x4 (колонки)")
    print(f"  {'size':>9}{'baseline':>11}{'numpy':>10}{'proc x4':>10}")
    with ProcessPoolExecutor(max_workers=4) as warm:
        stats_processes_columns(columns, 4, warm)
        for size in (10_000, 50_000, 200_000, 500_000):
            subset = students[:size] if size <= len(students) else make_students(size, seed=1)
            sub_columns = to_columns(subset)
            tb = measure("b", partial(compute_stats, subset), repeats=3).best
            tn = measure("n", partial(compute_stats_numpy_from_students, subset), repeats=3).best
            tp = measure("p", partial(stats_processes_columns, sub_columns, 4, warm), repeats=3).best
            print(f"  {size:>9}{tb:>11.4f}{tn:>10.4f}{tp:>10.4f}")
            rows += [{"size": size, "method": m, "best": round(t, 5), "mean": "", "speedup": round(tb / t, 3)}
                     for m, t in (("baseline", tb), ("numpy", tn), ("processes x4 warm", tp))]

    show("Кешування статистики групи (lru_cache, ключ = код + версія даних)")
    service = GroupStatisticsService(students)
    t_cold = measure("cold", partial(service.group_statistics, "ФЕП-31"), repeats=1).best
    t_warm = measure("warm", partial(service.group_statistics, "ФЕП-31"), repeats=5).best
    print(f"  cold (miss): {t_cold * 1000:.2f} ms; warm (hit): {t_warm * 1e6:.1f} µs; speedup {t_cold / t_warm:,.0f}×".replace(",", " "))
    for code in ("ФЕП-31", "ФЕП-32", "ФЕП-31", "ФЕП-33", "ФЕП-32"):
        service.group_statistics(code)
    print("  після 5 запитів (3 різні групи): hits, misses, size =", service.info())
    service.add(students[0])
    service.group_statistics("ФЕП-31")
    print("  після add() (версія змінилась) запит ФЕП-31 знову miss:", service.info())
    service.invalidate()
    print("  після invalidate():", service.info())

    show("Race condition: 4 потоки × 200 000 інкрементів (switch interval 5 ms за замовчуванням, потім 1 µs)")
    for interval in (None, 1e-6):
        label = "5 ms (default)" if interval is None else "1 µs"
        unsafe = race(200_000, 4, use_lock=False, switch_interval=interval)
        safe = race(200_000, 4, use_lock=True, switch_interval=interval)
        print(f"  switch interval {label:<15} без Lock: {unsafe:>7} із 800000 (втрачено {800_000 - unsafe:>6}); з Lock: {safe}")
    t_unsafe = measure("nolock", partial(race, 200_000, 4, use_lock=False), repeats=3).best
    t_safe = measure("lock", partial(race, 200_000, 4, use_lock=True), repeats=3).best
    print(f"  час: без Lock {t_unsafe:.3f} s, з Lock {t_safe:.3f} s — синхронізація коштує {t_safe / t_unsafe:.1f}×")

    args.csv.parent.mkdir(exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["size", "method", "best", "mean", "speedup"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nрезультати збережено: {args.csv} ({len(rows)} рядків)")


if __name__ == "__main__":
    main()
