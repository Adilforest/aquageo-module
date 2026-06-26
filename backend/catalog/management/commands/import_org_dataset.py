"""Import the organizers' canal dataset (datasetFromOrganizators.xls).

Separate from import_data (open sources). Objects get no geometry and
needs_geocoding=True. Idempotent by attributes.source_key.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog.org_import import import_rows

DEFAULT_PATH = Path(settings.BASE_DIR).parent / "data" / "datasetFromOrganizators.xls"


class Command(BaseCommand):
    help = "Import canals from the organizers' .xls (no geometry, needs_geocoding)."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(DEFAULT_PATH))
        parser.add_argument("--sheet", default="каналы")
        parser.add_argument("--skiprows", type=int, default=7)

    def handle(self, *args, **opts):
        import xlrd

        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"Dataset not found: {path}")

        sheet = xlrd.open_workbook(str(path)).sheet_by_name(opts["sheet"])
        rows = [sheet.row_values(i) for i in range(opts["skiprows"], sheet.nrows)]
        created, skipped = import_rows(rows)

        from catalog.models import Structure

        self.stdout.write(self.style.SUCCESS(
            f"Org dataset: created {created}, skipped {skipped} (already present)."
        ))
        self.stdout.write(
            f"Catalog totals: {Structure.objects.count()} structures, "
            f"{Structure.objects.filter(needs_geocoding=True).count()} need geocoding."
        )
