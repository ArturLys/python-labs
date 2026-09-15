"""Dependency injection: the store created in the lifespan, and the optional API token check."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from student_manager.api.store import StudentStore
from student_manager.settings import Settings


def get_store(request: Request) -> StudentStore:
    store: StudentStore = request.app.state.store
    return store


def require_token(request: Request, x_api_token: Annotated[str | None, Header()] = None) -> None:
    """Mutating endpoints are open in development; with API_TOKEN set they need the matching header.
    compare_digest keeps the comparison constant-time, so the token cannot be guessed byte by byte."""
    settings: Settings = request.app.state.settings
    if settings.api_token is None:
        return
    if x_api_token is None or not secrets.compare_digest(x_api_token, settings.api_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="потрібен коректний заголовок X-API-Token")
