"""Structural interfaces. Nothing here is inherited from — an object fits when its shape fits.

Three small protocols instead of one big one (interface segregation): the repository needs only
an id, the exporter needs only to_dict(), the services need only send().
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


class HasId(Protocol):
    """Anything a repository can store. Declared as a property so read-only ids satisfy it."""

    @property
    def id(self) -> int: ...


@runtime_checkable
class Serializable(Protocol):
    """Can turn itself into a plain mapping; runtime_checkable so isinstance() works on mixed input."""

    def to_dict(self) -> Mapping[str, object]: ...


class Notifier(Protocol):
    """Delivery channel for messages to a person. Console today, e-mail or a queue later."""

    def send(self, recipient: str, message: str) -> None: ...
