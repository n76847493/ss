"""PDF and CSV statement generation."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..db.models import Transaction, User
from .history import HistoryFilter


def _fmt(tx: Transaction) -> list[str]:
    return [
        tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        tx.type.value,
        tx.status.value,
        tx.chain.value,
        tx.asset.value,
        f"{tx.amount:.8f}",
        f"{tx.fee:.8f}" if tx.fee else "",
        tx.address_from or "",
        tx.address_to or "",
        tx.txid or "",
    ]


HEADER = [
    "Date (UTC)", "Type", "Status", "Chain", "Asset",
    "Amount", "Fee", "From", "To", "Tx hash",
]


def build_csv(user: User, txs: list[Transaction], f: HistoryFilter) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"Statement for user {user.telegram_id} ({user.username or ''})"])
    writer.writerow([
        f"Period: {f.date_from or 'all-time'} - {f.date_to or datetime.now(UTC)}",
        f"Filters: chain={f.chain.value if f.chain else 'any'}, "
        f"asset={f.asset.value if f.asset else 'any'}, "
        f"type={f.tx_type.value if f.tx_type else 'any'}",
    ])
    writer.writerow([])
    writer.writerow(HEADER)
    for tx in txs:
        writer.writerow(_fmt(tx))
    return buf.getvalue().encode("utf-8")


def build_pdf(user: User, txs: list[Transaction], f: HistoryFilter) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Wallet statement {user.telegram_id}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "T", parent=styles["Title"], fontSize=14, spaceAfter=4
    )
    meta_style = ParagraphStyle(
        "M", parent=styles["BodyText"], fontSize=9, textColor=colors.grey
    )

    elements = []
    elements.append(Paragraph("Wallet statement", title_style))
    elements.append(Paragraph(
        f"User: {user.telegram_id} (@{user.username or '-'})", meta_style
    ))
    elements.append(Paragraph(
        f"Period: {f.date_from or 'all-time'} — {f.date_to or datetime.now(UTC).replace(microsecond=0)}",
        meta_style,
    ))
    elements.append(Paragraph(
        f"Filters: chain={f.chain.value if f.chain else 'any'} "
        f"asset={f.asset.value if f.asset else 'any'} "
        f"type={f.tx_type.value if f.tx_type else 'any'}",
        meta_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # Use Paragraphs for wrapping in narrow columns.
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=7, leading=8)
    head = ParagraphStyle("head", parent=styles["BodyText"], fontSize=8, leading=9,
                          textColor=colors.whitesmoke)

    data = [[Paragraph(h, head) for h in HEADER]]
    for tx in txs:
        data.append([Paragraph(_truncate(v, 24), cell) for v in _fmt(tx)])
    if len(data) == 1:
        data.append([Paragraph("(no transactions)", cell)] + [Paragraph("", cell)] * (len(HEADER) - 1))

    col_widths = [22, 16, 16, 14, 12, 18, 12, 28, 28, 28]
    col_widths = [w * mm for w in col_widths]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F5F7FA")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()


def _truncate(s: str, n: int) -> str:
    if not s:
        return ""
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"
