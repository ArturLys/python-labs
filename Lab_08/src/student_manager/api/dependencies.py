"""Dependency injection: endpoints ask for a StudentStore and get the one created in the app's lifespan."""

from __future__ import annotations

from fastapi import Request

from student_manager.api.store import StudentStore


def get_store(request: Request) -> StudentStore:
    store: StudentStore = request.app.state.store
    return store
