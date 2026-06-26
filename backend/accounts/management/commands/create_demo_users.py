"""Create deterministic demo accounts for the defence/demo (issue #34).

Idempotent: if a user already exists its password is reset to the known value
and its role is corrected (so the demo logins always work). Passwords are fixed
and printed at the end — these are DEMO credentials, not for production.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from accounts.models import Role, User

# (username, password, role, is_superuser, what they can do on the demo)
DEMO_USERS = [
    ("viewer", "aquageo-viewer", Role.VIEWER, False,
     "Карта, каталог, дашборд (только просмотр)."),
    ("engineer", "aquageo-engineer", Role.ENGINEER, False,
     "Просмотр + ИИ-парсинг (/parse), создание черновиков, подача заявки."),
    ("manager", "aquageo-manager", Role.MANAGER, False,
     "Согласование/отклонение заявок, ЭЦП-заглушка и PDF-приказ, видит всё."),
    ("admin", "aquageo-admin", Role.ADMIN, True,
     "Полный доступ + админка Django /admin/ (суперпользователь)."),
]


class Command(BaseCommand):
    help = "Create/refresh deterministic demo accounts (one per role) and print them."

    def handle(self, *args, **options):
        rows = []
        for username, password, role, is_superuser, desc in DEMO_USERS:
            user, created = User.objects.get_or_create(username=username)
            user.role = role
            user.is_staff = is_superuser
            user.is_superuser = is_superuser
            if not user.email:
                user.email = f"{username}@aquageo.demo"
            user.set_password(password)
            user.save()
            rows.append((username, password, role, "создан" if created else "обновлён", desc))

        # Pretty table to stdout.
        self.stdout.write(self.style.SUCCESS("\nДемо-аккаунты (логин / пароль / роль):"))
        header = f"{'ЛОГИН':<10} {'ПАРОЛЬ':<18} {'РОЛЬ':<10} {'СТАТУС':<9} ОПИСАНИЕ"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for username, password, role, status, desc in rows:
            self.stdout.write(
                f"{username:<10} {password:<18} {role:<10} {status:<9} {desc}"
            )
        self.stdout.write("")
