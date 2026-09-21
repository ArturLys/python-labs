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
python -m records_app.main          # демонстрація на вбудованих даних
python -m records_app.main --menu   # інтерактивне меню
records-app --version               # console script з pyproject.toml
```

## Тести

```
python -m pytest
```

## Структура

```
src/records_app/
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
$ python -m records_app.main
УСІ СТУДЕНТИ
Студент                   Група      Середній бал
-------------------------------------------------
Гнатишин Марта            ФЕП-31с           93.40
...
Найкращий студент: Пасічник Ірина (ФЕП-32, 96.70)
```

## Автор

Лис Артур, група ФЕП-31с
