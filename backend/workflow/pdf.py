"""Approval order (приказ) PDF rendering via reportlab (#27)."""
import io


def render_order_pdf(application, number: str, issued_at) -> bytes:
    """Render a one-page approval order PDF and return it as bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    structure = application.structure
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"Приказ {number}",
    )
    flow = [
        Paragraph("ПРИКАЗ", styles["Title"]),
        Paragraph(f"№ {number}", styles["Heading2"]),
        Paragraph(
            f"от {issued_at.strftime('%d.%m.%Y')}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            "О согласовании и вводе объекта гидротехнической инфраструктуры в "
            "эксплуатацию (государственный реестр AquaGeo).",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    rows = [
        ["Объект", structure.name_ru or str(structure.pk)],
        ["Идентификатор", str(structure.pk)],
        ["Тип заявки", application.get_kind_display()],
        ["Заявка №", str(application.pk)],
        ["Решение", "СОГЛАСОВАНО"],
    ]
    table = Table(rows, colWidths=[45 * mm, 115 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D0DA")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 14 * mm))
    flow.append(Paragraph(
        "Подписано электронной цифровой подписью (демонстрационная заглушка).",
        styles["Italic"],
    ))

    doc.build(flow)
    return buf.getvalue()
