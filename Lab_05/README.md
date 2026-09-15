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

## Лабораторна робота №5

Пакет `storage` — надійний імпорт/експорт і конфігурація: винятки, файли, серіалізація.

```
python -m student_manager.storage                       # демонстрація, файли у data/ (не в Git)
python -m student_manager.storage run -c data/config.yaml   # один запуск за конфігурацією, код виходу 1 при помилці
python -m student_manager.storage experiments           # strict/tolerant та eager/streaming (tracemalloc)
student-storage --help                                  # той самий CLI як console script
```

```
src/student_manager/storage/
    exceptions.py       StorageError -> ConfigurationError, DataError -> Import/Export/RecordValidation
    dto.py              StudentRow (DTO файлів) <-> Student (модель ЛР1), GradeRecord (ЛР2)
    validators.py       перевірка id, name, group, grade 0..100, email; raise ... from ...
    config.py           config.yaml -> AppConfig (frozen dataclasses), валідація, STUDENT_MANAGER_* override
    logging_config.py   RotatingFileHandler + консоль
    context.py          AtomicWriter (__enter__/__exit__), logged_operation (@contextmanager), open_text (.gz)
    readers.py          Importer Protocol: CSV, JSON Lines (потокові), JSON, YAML; вибір за розширенням
    exporters.py        Exporter Protocol: CSV, JSON, JSON Lines, YAML через AtomicWriter; StorageJSONEncoder
    services.py         import_records (strict/tolerant), ImportStatistics, error_report, run_pipeline
    dataset.py          генератор демо-CSV і великих файлів для експериментів
    benchmark.py        експерименти 1 (strict vs tolerant) і 2 (eager vs streaming)
tests/test_storage.py
```

Залежності: `pyyaml` (runtime), `mypy` + `types-PyYAML` (група `dev`): `pip install -e ".[test,dev]"`.
