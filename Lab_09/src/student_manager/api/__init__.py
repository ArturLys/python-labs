"""REST API (FastAPI + Pydantic) and asynchronous HTTP client (HTTPX) — лабораторна робота №8."""

from student_manager.api.app import create_app
from student_manager.api.client import StudentApiClient
from student_manager.api.concurrency import gather_statistics, retry

__all__ = ["StudentApiClient", "create_app", "gather_statistics", "retry"]
