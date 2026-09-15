# Student Manager

Наскрізний навчальний проєкт курсу «Професійний Python» (ЛНУ ім. Івана Франка, ФЕП-31).
Варіант 1 — система обліку студентів: ім'я, прізвище, група, середній бал.

Лабораторна робота №1: структура проєкту (src-layout), модель даних, бізнес-логіка,
консольне меню, тести, Git.
Лабораторна робота №2: пакет `analytics` — обробка структурованих даних (оцінки за
дисциплінами): list/tuple/set/dict, collections, comprehensions, closures, decorators,
аналіз складності та benchmark пошуку list vs dict.

## Вимоги

Python 3.11+

## Встановлення

```
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[test]"
```

## Запуск

```
python -m student_manager.main          # демонстрація на вбудованих даних
python -m student_manager.main --menu   # інтерактивне меню
python -m student_manager.analytics     # аналіз успішності + benchmark (ЛР2)
student-manager --version               # console script з pyproject.toml
```

## Тести

```
python -m pytest
```

## Структура

```
src/student_manager/
    config.py       константи (межі оцінок, шаблон назви групи)
    exceptions.py   власні винятки предметної області
    models.py       dataclass Student з валідацією
    registry.py     StudentRegistry — уся бізнес-логіка
    cli.py          текстові таблиці та меню
    main.py         точка входу
    analytics/      ЛР2: data.py, processors.py, analytics.py, decorators.py, benchmark.py
tests/
    test_registry.py
    test_analytics.py
```

## Приклад

```
$ python -m student_manager.main
УСІ СТУДЕНТИ
Студент                   Група      Середній бал
-------------------------------------------------
Гнатишин Марта            ФЕП-31с           93.40
...
Найкращий студент: Пасічник Ірина (ФЕП-32, 96.70)
```

## Автор

Лис Артур, група ФЕП-31

## Лабораторна робота №3

Пакет `streaming` — потокова обробка результатів студентів (варіант 1): протокол ітерації,
власний iterator, генератори, `yield from`, generator expressions, itertools, lazy pipeline,
batching і експеримент eager проти lazy.

```
python -m student_manager.streaming     # демонстрація + експеримент; запускати з кореня проєкту
```

Перший запуск генерує CSV-файли в `data/` (200 000 рядків для демонстрації та
10 000 / 100 000 / 500 000 / 1 000 000 для експерименту, разом близько 90 MB). Каталог
`data/` не потрапляє в Git — комітиться генератор, а не дані. Інше місце для даних
задає змінна середовища `STUDENT_MANAGER_DATA`.

```
src/student_manager/streaming/
    models.py       StudentRecord — рядок student_id,name,group,grade
    generate.py     генератор синтетичних рядків (count + islice) і потоковий запис CSV
    readers.py      read_lines (generator), LineReader (iterator), CsvDataset (iterable)
    parsers.py      clean_lines, parse_rows (yield from DictReader), validate + ValidationReport
    filters.py      with_min_grade, in_groups, where, head_by_id (takewhile)
    transforms.py   tidy / normalize, to_grade_records — міст до пакета analytics
    batching.py     batched, adaptive_batches (islice), flatten (рекурсивний yield from)
    aggregates.py   streaming_stats, top_n (heapq), running_average (accumulate),
                    grade_changes (pairwise), by_group (groupby), find_first
    pipeline.py     traced (logging), assemble / build_pipeline, build_multi_pipeline (chain), export_csv
    experiment.py   eager vs lazy: час, peak memory (tracemalloc), time to first result, early termination
tests/test_streaming.py
```
