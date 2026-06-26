"""Generate the demo parsing fixtures (issue #22).

Writes two sample documents for the SAME new hydropost (not in the DB, with real
Jambyl coordinates) so the parsing demo shows "file -> object on the map":
  backend/data/samples/hydropost_sample.xlsx  (field/value table)
  backend/data/samples/hydropost_passport.pdf (ГТС passport, text layer)
These are committed fixtures (see .gitignore).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SAMPLES_DIR = Path(settings.BASE_DIR) / "data" / "samples"

# Demo object — coordinates in Jambyl (Shu-Talas), deliberately not an existing post.
FIELDS = [
    ("Наименование", "Гидропост Демо-Талас"),
    ("Тип", "Гидропост"),
    ("Река", "Талас"),
    ("Широта", "43.123456"),
    ("Долгота", "71.654321"),
    ("Опасный уровень, см", "350"),
    ("Год ввода", "2018"),
    ("Ответственная организация", "Казводхоз (демо)"),
]


class Command(BaseCommand):
    help = "Generate demo sample documents (xlsx + pdf) for the parsing demo."

    def handle(self, *args, **options):
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        self._write_xlsx(SAMPLES_DIR / "hydropost_sample.xlsx")
        self._write_pdf(SAMPLES_DIR / "hydropost_passport.pdf")
        self.stdout.write(self.style.SUCCESS(f"Sample docs written to {SAMPLES_DIR}"))

    def _write_xlsx(self, path: Path):
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "hydropost"
        ws.append(["Поле", "Значение"])
        for field, value in FIELDS:
            ws.append([field, value])
        wb.save(path)

    def _write_pdf(self, path: Path):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        # Register a Cyrillic-capable font so the passport text renders/extracts.
        font = "Helvetica"
        ttf = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if Path(ttf).exists():
            pdfmetrics.registerFont(TTFont("DejaVu", ttf))
            font = "DejaVu"

        c = canvas.Canvas(str(path), pagesize=A4)
        _, height = A4
        y = height - 60
        c.setFont(font, 14)
        c.drawString(50, y, "ПАСПОРТ ГИДРОТЕХНИЧЕСКОГО СООРУЖЕНИЯ")
        c.setFont(font, 11)
        y -= 30
        for field, value in FIELDS:
            c.drawString(50, y, f"{field}: {value}")
            y -= 22
        c.showPage()
        c.save()
