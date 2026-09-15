"""Runtime configuration from environment variables (12-factor). Nothing secret lives in the code.

DATABASE_URL, APP_ENV, LOG_LEVEL, API_HOST, API_PORT and the secret API_TOKEN are read once at start-up;
`.env` is loaded only if present (development), never committed (see .gitignore and .env.example).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

AppEnv = Literal["development", "test", "production"]
APP_ENVS: tuple[AppEnv, ...] = ("development", "test", "production")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
SECRET_KEYS = ("api_token",)
DEFAULT_DATABASE_URL = "sqlite:///data/students.db"
DEFAULT_API_HOST = "127.0.0.1"


class SettingsError(ValueError):
    """A required variable is missing or has an invalid value; the process must not start."""


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    app_env: AppEnv = "development"
    log_level: str = "INFO"
    api_host: str = DEFAULT_API_HOST
    api_port: int = 8000
    api_token: str | None = None  # secret: when set, POST/PATCH/DELETE require the X-API-Token header

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        app_env = env.get("APP_ENV", "development").strip().lower()
        if app_env not in APP_ENVS:
            raise SettingsError(f"APP_ENV має бути одним із {', '.join(APP_ENVS)}, отримано {app_env!r}")
        level = env.get("LOG_LEVEL", "INFO").strip().upper()
        if level not in LOG_LEVELS:
            raise SettingsError(f"LOG_LEVEL має бути одним із {', '.join(LOG_LEVELS)}, отримано {level!r}")
        try:
            port = int(env.get("API_PORT", "8000"))
        except ValueError as error:
            raise SettingsError(f"API_PORT має бути цілим числом: {error}") from error
        token = env.get("API_TOKEN", "").strip() or None
        if app_env == "production" and token is None:
            raise SettingsError("у production API_TOKEN обов'язковий (передайте його через середовище, не через код)")
        return cls(
            database_url=env.get("DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL,
            app_env=app_env,
            log_level=level,
            api_host=env.get("API_HOST", DEFAULT_API_HOST),
            api_port=port,
            api_token=token,
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def redacted(self) -> dict[str, object]:
        """Safe to log: secrets are masked, presence is still visible."""
        data = asdict(self)
        for key in SECRET_KEYS:
            if data.get(key):
                data[key] = "***"
        return data


def load_dotenv(path: Path = Path(".env"), *, environ: dict[str, str] | None = None) -> list[str]:
    """Tiny .env reader: KEY=VALUE lines, # comments, no override of variables already set. Returns the keys set."""
    target = os.environ if environ is None else environ
    if not path.is_file():
        return []
    applied: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in target:
            target[key] = value
            applied.append(key)
    return applied


def configure_logging(level: str) -> None:
    """One root configuration for the process; `force` replaces handlers left by libraries or earlier runs."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
