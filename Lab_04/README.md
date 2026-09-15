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
