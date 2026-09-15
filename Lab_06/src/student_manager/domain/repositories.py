"""Storage abstraction and its in-memory implementation.

Repository[T] is the seam between the domain and infrastructure: services depend on the abstract
class, the demo plugs in a dict-backed one, a database-backed one comes in a later lab without a
single change in the services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from typing import Generic, TypeVar

from student_manager.domain.errors import DuplicateEntityError, EntityNotFoundError
from student_manager.domain.protocols import HasId

# Bound TypeVar: T may be any type, as long as it structurally has an `id`.
T = TypeVar("T", bound=HasId)


class Repository(ABC, Generic[T]):
    """Abstract contract. The concrete helpers (require, __contains__, __len__) are built on the
    abstract primitives, so every implementation gets them for free."""

    @abstractmethod
    def add(self, item: T) -> None: ...

    @abstractmethod
    def get(self, item_id: int) -> T | None: ...

    @abstractmethod
    def all(self) -> list[T]: ...

    @abstractmethod
    def remove(self, item_id: int) -> bool: ...

    def require(self, item_id: int) -> T:
        """get() that raises instead of returning None; keeps `if x is None` out of the services."""
        item = self.get(item_id)
        if item is None:
            raise EntityNotFoundError(self.kind, item_id)
        return item

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self.all() if predicate(item)]

    @property
    def kind(self) -> str:
        """Human name of the stored type for error messages; overridable."""
        return "об'єкт"

    def __contains__(self, item_id: object) -> bool:
        return isinstance(item_id, int) and self.get(item_id) is not None

    def __len__(self) -> int:
        return len(self.all())


class InMemoryRepository(Repository[T]):
    """dict-backed repository, parameterised at the call site: InMemoryRepository[Student]()."""

    def __init__(self, items: Iterable[T] = (), kind: str = "об'єкт") -> None:
        self._items: dict[int, T] = {}
        self._kind = kind
        for item in items:
            self.add(item)

    def add(self, item: T) -> None:
        if item.id in self._items:
            raise DuplicateEntityError(f"{self._kind} з id={item.id} уже існує")
        self._items[item.id] = item

    def get(self, item_id: int) -> T | None:
        return self._items.get(item_id)

    def all(self) -> list[T]:
        return list(self._items.values())

    def remove(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None

    @property
    def kind(self) -> str:
        return self._kind

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __repr__(self) -> str:
        return f"InMemoryRepository[{self._kind}]({len(self)} items)"
