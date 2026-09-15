"""Outbound side effects (notifications, remote gateway) behind narrow interfaces, so tests can replace them."""

from student_manager.notify.async_service import AsyncStudentService, StudentGateway
from student_manager.notify.digest import DigestSender, Mailer

__all__ = ["AsyncStudentService", "DigestSender", "Mailer", "StudentGateway"]
