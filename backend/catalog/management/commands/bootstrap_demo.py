"""One-command demo bootstrap (issue #34).

Runs the full chain to get a believable demo from an empty database:

    reference -> import open data -> hydropost history -> realistic demo seed
    -> recompute assessments -> demo users

Import steps need the raw datasets in ``backend/data`` (gitignored). If they are
absent the step is skipped with a warning so the rest still runs (the catalog
will just be smaller). Every step is idempotent.
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed reference + import + demo seed + recompute + demo users (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-import", action="store_true",
            help="Skip open-data import (use when raw datasets are not present).",
        )
        parser.add_argument(
            "--fresh-share", type=float, default=0.88,
            help="Passed to seed_demo (fraction of objects with a fresh inspection).",
        )

    def _step(self, title, fn, *, required=False):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {title} ==="))
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - keep going on optional steps
            if required:
                raise CommandError(f"{title}: {exc}") from exc
            self.stdout.write(self.style.WARNING(f"  пропущено: {exc}"))

    def handle(self, *args, **options):
        skip_import = options["skip_import"]
        fresh_share = options["fresh_share"]

        self._step("Справочники (seed_reference)",
                   lambda: call_command("seed_reference"), required=True)

        if not skip_import:
            self._step("Импорт открытых данных (import_data)",
                       lambda: call_command("import_data"))
            self._step("Импорт каналов организаторов (import_org_dataset)",
                       lambda: call_command("import_org_dataset"))
            self._step("История гидропостов (generate_hydropost_history)",
                       lambda: call_command("generate_hydropost_history"))

        self._step("Реалистичный демо-сид (seed_demo)",
                   lambda: call_command("seed_demo", fresh_share=fresh_share),
                   required=True)
        self._step("Пересчёт оценок (recompute_assessments)",
                   lambda: call_command("recompute_assessments"), required=True)
        self._step("Демо-аккаунты (create_demo_users)",
                   lambda: call_command("create_demo_users"), required=True)

        self.stdout.write(self.style.SUCCESS("\nГотово: демо-данные и аккаунты созданы."))
