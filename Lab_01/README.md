# Student Manager

Наскрізний навчальний проєкт курсу «Професійний Python» (ЛНУ ім. Івана Франка, ФЕП-31с).
Варіант 1 — система обліку студентів: ім'я, прізвище, група, середній бал.

Лабораторна робота №1: структура проєкту (src-layout), модель даних, бізнес-логіка,
консольне меню, тести, Git.

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
tests/
    test_registry.py
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

Лис Артур, група ФЕП-31с
