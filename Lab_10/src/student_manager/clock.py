"""The one place the project asks what time it is.

Production code calls ``clock.now()``; a test replaces the attribute with ``monkeypatch.setattr`` and gets
a deterministic timestamp without patching ``datetime`` itself (which is a C type and cannot be patched).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime


def _system_now() -> datetime:
    return datetime.now(tz=UTC)


now: Callable[[], datetime] = _system_now
