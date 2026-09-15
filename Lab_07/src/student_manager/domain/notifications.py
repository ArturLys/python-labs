"""Concrete notifiers. Neither inherits from the Notifier protocol — they simply have send()."""

from __future__ import annotations


class ConsoleNotifier:
    """Prints the message; what the demo uses."""

    def send(self, recipient: str, message: str) -> None:
        print(f"  [повідомлення → {recipient}] {message}")


class RecordingNotifier:
    """Keeps every message in a list instead of delivering it; what the tests inject."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.sent.append((recipient, message))

    def __len__(self) -> int:
        return len(self.sent)
