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

## Лабораторна робота №4

Пакет `student_manager.domain` — типізована об'єктна модель предметної області, на якій
будуватимуться наступні роботи (база даних, REST API). Dataclass `Student` з ЛР1 лишається
мінімальною моделлю для консольного меню; `domain` — його професійний наступник.

```
src/student_manager/domain/
    value_objects.py  frozen dataclass: PersonName, GroupCode, Grade (total_ordering), Credits (__add__)
    models.py         сутності Entity -> Person -> Student / Teacher; Course; Group; колекція GradeBook
    errors.py         DomainError та нащадки поверх StudentManagerError з ЛР1
    protocols.py      HasId, Serializable (runtime_checkable), Notifier
    repositories.py   Repository[T] (ABC, Generic, bound TypeVar) та InMemoryRepository[T]
    dto.py            TypedDict: StudentPayload (NotRequired email), GradePayload, StudentReport, GroupReport
    services.py       EnrollmentService, GradingService, ReportingService; strategy AcademicStatusPolicy
    notifications.py  ConsoleNotifier, RecordingNotifier
    container.py      ручний DI-контейнер (composition root)
    importing.py      експеримент inheritance vs composition (імпорт оцінок)
    __main__.py       демонстраційний сценарій
```

Запуск і перевірка (CI-подібна команда):

```
python -m student_manager.domain
python -m mypy src --strict && python -m pytest -q
```

`[tool.mypy]` у `pyproject.toml` вмикає strict-режим; mypy встановлюється групою `dev`:
`python -m pip install -e ".[test,dev]"`.

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

## Лабораторна робота №6 — автоматизоване тестування

Тести переструктуровано у `tests/conftest.py` (спільні фікстури), `tests/unit/` (по одному модулю на
пакет) та `tests/integration/` (файли у `tmp_path`, конфігурація, контейнер ЛР4). Нові «шви» у продакшн-коді,
які тестуються через дублери: `student_manager.clock` (детермінований час), `student_manager.snapshot`,
`student_manager.notify` (`DigestSender` + протокол `Mailer`, `AsyncStudentService` + протокол `StudentGateway`).

```bash
pip install -e ".[test]"
pytest                                   # 175 тестів, маркери integration/slow
pytest -m "not slow"                     # без довгих
pytest -m integration                    # лише інтеграційні
pytest --cov=student_manager --cov-branch --cov-report=term-missing --cov-report=html
```

Поріг покриття (`fail_under = 80`, гілки увімкнено) і маркери оголошено в `pyproject.toml`; демонстраційні
`__main__.py` та `benchmark.py` виключено з покриття.

## Лабораторна робота №7 — persistence layer (SQLite, SQLAlchemy, Alembic)

Пакет `student_manager.db`: ORM-моделі `GroupRecord` 1—* `StudentRecord` (`orm.py`), engine/session factory та
`session_scope` (`engine.py`), `SqlRepository[T]` + `StudentRepository`/`GroupRepository` (`repositories.py`),
транзакційний `StudentService` (`services.py`), DB-API-варіант тих самих таблиць (`raw.py`).
Схема створюється міграціями Alembic (`migrations/versions/0001_*`, `0002_*` — поле `email`).

```bash
pip install -e ".[db]"
alembic upgrade head                 # data/students.db
alembic downgrade -1                 # відкотити міграцію email
python -m student_manager.db         # демонстрація DB-API, CRUD, транзакцій і міграцій
pytest tests/integration/test_db.py -v
```

## Лабораторна робота №8 — REST API (FastAPI, Pydantic, asyncio, HTTPX)

Пакет `student_manager.api`: `schemas.py` (Pydantic), `store.py` (репозиторії ЛР7 → схеми), `routers/`
(`students`, `groups`, `debug`), `app.py` (фабрика застосунку, lifespan, exception handlers),
`concurrency.py` (Task + gather + Semaphore + timeout, retry з exponential backoff), `client.py`
(`httpx.AsyncClient`-клієнт з retry/timeout/Semaphore).

```bash
pip install -e ".[api]"
python -m student_manager.api serve          # http://127.0.0.1:8000/docs — Swagger UI
python -m student_manager.api demo           # сценарій через httpx.ASGITransport, без сервера
pytest tests/integration/test_api.py -v
```

| Метод | Шлях | Призначення |
|-------|------|-------------|
| GET | /students | список: `last_name`, `group`, `sort`, `page`, `size` |
| GET | /students/best?group= | найкращий студент |
| GET | /students/{id} | один студент |
| POST | /students | створити (201) |
| PATCH | /students/{id} | бал / група / email |
| DELETE | /students/{id} | видалити (204) |
| GET | /groups | усі групи зі статистикою |
| GET | /groups/statistics?code=A&code=B | кілька груп одночасно (gather) |
| GET | /groups/{code}/students | студенти групи |
| GET | /groups/{code}/statistics | середній бал, кількість, найкращий |
