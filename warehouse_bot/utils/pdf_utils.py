# -*- coding: utf-8 -*-
import os
from typing import List, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_NAME = "Helvetica"
_CANDIDATE_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\DejaVuSans.ttf",
]


def _register_unicode_font() -> str:
    """Kirill / o'zbek maxsus belgilarini to'g'ri chiqarish uchun Unicode shrift
    topilsa ro'yxatdan o'tkazadi, aks holda standart Helvetica ishlatiladi
    (bu holda kirillcha matn to'g'ri chiqmasligi mumkin)."""
    global _FONT_NAME
    for path in _CANDIDATE_FONTS:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CustomUnicodeFont", path))
                _FONT_NAME = "CustomUnicodeFont"
                return _FONT_NAME
            except Exception:
                continue
    return _FONT_NAME


def export_products_to_pdf(products: List[Dict[str, Any]], filepath: str, title: str = "Mahsulotlar hisoboti") -> None:
    font_name = _register_unicode_font()
    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 0.5 * cm)]

    headers = ["Nomi", "Kodi", "Kategoriya", "Subkategoriya", "Format", "Qalinlik", "Miqdor", "Joylashuv", "Qo'shilgan"]
    data = [headers]
    for p in products:
        data.append(
            [
                str(p.get("name", "")),
                str(p.get("code", "")),
                str(p.get("category", "")),
                str(p.get("subcategory", "")),
                str(p.get("format_size", "")),
                str(p.get("thickness", "")),
                str(p.get("quantity", "")),
                str(p.get("location", "")),
                str(p.get("added_at", "")),
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4053")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F3F4")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
