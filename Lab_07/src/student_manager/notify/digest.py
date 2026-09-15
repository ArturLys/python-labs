"""Weekly digest: one message per group with its average and the best student.

The mailer is injected. In production it is an SMTP client; in tests it is a ``Mock`` whose calls are
inspected — nothing here knows the difference, and that is the point of the seam.
"""

from __future__ import annotations

from typing import Protocol

from student_manager.exceptions import StudentManagerError
from student_manager.registry import StudentRegistry


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> str:
        """Return the message id assigned by the transport."""
        ...


class DigestError(StudentManagerError):
    """The transport refused a message; the digest reports which group it was."""


class DigestSender:
    def __init__(self, mailer: Mailer, *, sender_domain: str = "lnu.edu.ua") -> None:
        self._mailer = mailer
        self._domain = sender_domain

    def recipient_for(self, group: str) -> str:
        return f"{group.lower()}@{self._domain}"

    def compose(self, registry: StudentRegistry, group: str) -> tuple[str, str]:
        average = registry.group_average(group)
        best = registry.best(group)
        subject = f"Дайджест групи {group}"
        body = f"Середній бал: {average:.1f}. Найкращий результат: {best.full_name} ({best.average_grade:g})."
        return subject, body

    def send_all(self, registry: StudentRegistry) -> dict[str, str]:
        """Send one digest per group; return {group: message id}. A transport failure stops the run."""
        sent: dict[str, str] = {}
        for group in registry.groups():
            subject, body = self.compose(registry, group)
            try:
                sent[group] = self._mailer.send(self.recipient_for(group), subject, body)
            except OSError as error:
                raise DigestError(f"не вдалося надіслати дайджест групі {group}: {error}") from error
        return sent
