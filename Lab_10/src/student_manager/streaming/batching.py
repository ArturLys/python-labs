"""Batching stage: fixed-size and adaptive batches cut from a stream with islice, plus a recursive flatten."""

from __future__ import annotations

from collections.abc import Generator, Iterable, Iterator
from itertools import islice
from typing import TypeAlias, TypeVar

T = TypeVar("T")

Nested: TypeAlias = T | list["Nested[T]"]  # a leaf or a list of leaves/lists, any depth


def batched(items: Iterable[T], size: int) -> Generator[list[T], None, None]:
    """Fixed-size batches; only the current batch is materialised, the rest of the stream stays lazy."""
    if size < 1:
        raise ValueError("batch size must be positive")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def adaptive_batches(items: Iterable[T], start: int = 1, limit: int = 1_000) -> Generator[list[T], None, None]:
    """Dynamic batching: the batch doubles after every step up to `limit` (like TCP slow start).

    Handy when the consumer (an API, a database) should be warmed up before it receives full-size chunks.
    """
    if start < 1 or limit < start:
        raise ValueError("need 1 <= start <= limit")
    iterator = iter(items)
    size = start
    while batch := list(islice(iterator, size)):
        yield batch
        size = min(size * 2, limit)


def flatten(values: Iterable[Nested[T]]) -> Iterator[T]:
    """Recursive generator: nested lists of any depth (batches of batches) back into one flat stream."""
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value
