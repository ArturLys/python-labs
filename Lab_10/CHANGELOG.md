# Changelog

Версії за [Semantic Versioning](https://semver.org/lang/uk/): MAJOR — несумісні зміни API, MINOR — нові
можливості, PATCH — виправлення.

## [1.0.0] — 2026-09-08 (ЛР10)
- Пакет готовий до production: `python -m build` дає wheel і sdist, `student-api` — консольна команда.
- Конфігурація через середовище: `DATABASE_URL`, `APP_ENV`, `LOG_LEVEL`, `API_HOST`, `API_PORT`, секрет `API_TOKEN`.
- `GET /health`; захист POST/PATCH/DELETE заголовком `X-API-Token`, коли задано `API_TOKEN`.
- Dockerfile (multi-stage, non-root, HEALTHCHECK, міграції при старті), docker-compose, `.dockerignore`.
- GitHub Actions: ruff, mypy, pytest (3.12/3.13, coverage ≥ 80 %), build wheel/sdist, docker build + `/health`.

## [0.9.0] — ЛР9: профілювання та оптимізація (`student_manager.perf`)
## [0.8.0] — ЛР8: REST API на FastAPI, asyncio, HTTPX-клієнт (`student_manager.api`)
## [0.7.0] — ЛР7: SQLite, SQLAlchemy ORM, репозиторії, Alembic (`student_manager.db`)
## [0.6.0] — ЛР6: тестова інфраструктура, фікстури, моки, coverage
## [0.5.0] — ЛР5: імпорт/експорт, конфігурація YAML, logging (`student_manager.storage`)
## [0.4.0] — ЛР4: доменна модель ООП (`student_manager.domain`)
## [0.3.0] — ЛР3: генератори та потокова обробка (`student_manager.streaming`)
## [0.2.0] — ЛР2: аналітика, функції вищого порядку (`student_manager.analytics`)
## [0.1.0] — ЛР1: модель `Student`, реєстр, консольний інтерфейс
