"""Lab 10: settings from the environment, .env loading, /health, and the API token protecting mutations."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from student_manager import __version__
from student_manager.api import create_app
from student_manager.settings import Settings, SettingsError, load_dotenv

STUDENT = {"first_name": "Марта", "last_name": "Гнатишин", "group": "ФЕП-31с", "average_grade": 93.4}


def test_settings_defaults_come_from_an_empty_environment() -> None:
    settings = Settings.from_env({})
    assert settings.app_env == "development" and settings.log_level == "INFO" and settings.api_port == 8000
    assert settings.api_token is None and not settings.is_production


def test_settings_read_every_variable_and_redact_the_secret() -> None:
    settings = Settings.from_env(
        {
            "DATABASE_URL": "sqlite:////data/x.db",
            "APP_ENV": "production",
            "LOG_LEVEL": "debug",
            "API_HOST": "0.0.0.0",
            "API_PORT": "9000",
            "API_TOKEN": "s3cret",
        }
    )
    assert settings.database_url == "sqlite:////data/x.db" and settings.is_production
    assert settings.log_level == "DEBUG" and settings.api_port == 9000 and settings.api_token == "s3cret"
    assert settings.redacted()["api_token"] == "***"


@pytest.mark.parametrize(
    "environ",
    [
        {"APP_ENV": "staging"},
        {"LOG_LEVEL": "LOUD"},
        {"API_PORT": "eighty"},
        {"APP_ENV": "production"},
    ],
    ids=["bad-env", "bad-level", "bad-port", "production-without-token"],
)
def test_invalid_settings_fail_fast(environ: dict[str, str]) -> None:
    with pytest.raises(SettingsError):
        Settings.from_env(environ)


def test_dotenv_does_not_override_real_environment(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nAPP_ENV=test\nLOG_LEVEL='WARNING'\nAPI_TOKEN=from-file\n\n", encoding="utf-8")
    environ = {"API_TOKEN": "from-shell"}
    assert load_dotenv(env_file, environ=environ) == ["APP_ENV", "LOG_LEVEL"]
    assert environ == {"API_TOKEN": "from-shell", "APP_ENV": "test", "LOG_LEVEL": "WARNING"}
    assert load_dotenv(tmp_path / "missing.env", environ=environ) == []


async def test_health_reports_version_environment_and_database(tmp_path: Path) -> None:
    settings = Settings.from_env({"APP_ENV": "test", "LOG_LEVEL": "WARNING"})
    app = create_app(settings, database_url=f"sqlite:///{(tmp_path / 'h.db').as_posix()}")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
            response = await api.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "app_env": "test", "database": "ok"}


async def test_mutations_require_the_token_when_it_is_configured(tmp_path: Path) -> None:
    settings = Settings.from_env({"APP_ENV": "production", "API_TOKEN": "s3cret", "LOG_LEVEL": "WARNING"})
    app = create_app(settings, database_url=f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
            assert (await api.post("/students", json=STUDENT)).status_code == 401
            assert (await api.post("/students", json=STUDENT, headers={"X-API-Token": "wrong"})).status_code == 401
            created = await api.post("/students", json=STUDENT, headers={"X-API-Token": "s3cret"})
            assert created.status_code == 201
            assert (await api.get("/students/1")).status_code == 200  # reads stay open
            assert (await api.delete("/students/1")).status_code == 401
            assert (await api.get("/debug/slow")).status_code == 404  # debug router is off in production
