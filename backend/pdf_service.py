"""PDF generation service for quotations and invoices using ReportLab."""
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


BRAND_BLACK = colors.HexColor("#111111")
BRAND_BLUE = colors.HexColor("#002FA7")
GREY_LIGHT = colors.HexColor("#F1F1EF")
GREY_BORDER = colors.HexColor("#D4D4D2")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="TitleBig", fontName="Helvetica-Bold", fontSize=22, textColor=BRAND_BLACK, spaceAfter=4))
    ss.add(ParagraphStyle(name="Muted", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555555")))
    ss.add(ParagraphStyle(name="Label", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#555555")))
    ss.add(ParagraphStyle(name="Body9", fontName="Helvetica", fontSize=9, textColor=BRAND_BLACK, leading=12))
    ss.add(ParagraphStyle(name="Body10Bold", fontName="Helvetica-Bold", fontSize=10, textColor=BRAND_BLACK))
    return ss


def _fmt_money(v, currency="IDR"):
    try:
        return f"{currency} {float(v):,.2f}"
    except Exception:
        return f"{currency} 0.00"


def _compute_totals(items):
    subtotal = 0.0
    total_discount = 0.0
    total_tax = 0.0
    grand = 0.0
    for it in items:
        qty = float(it.get("quantity", 0))
        up = float(it.get("unit_price", 0))
        disc = float(it.get("discount_percent", 0))
        tax = float(it.get("tax_percent", 0))
        sub = qty * up
        d_amt = sub * disc / 100
        after_d = sub - d_amt
        t_amt = after_d * tax / 100
        line = after_d + t_amt
        subtotal += sub
        total_discount += d_amt
        total_tax += t_amt
        grand += line
    return subtotal, total_discount, total_tax, grand


def build_document_pdf(kind: str, doc: dict, customer: dict, settings: dict) -> bytes:
    """kind: 'quotation' or 'invoice'."""
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    ss = _styles()
    story = []

    company_name = settings.get("company_name", "LogiSource Digital")
    tagline = settings.get("company_tagline", "")
    currency = doc.get("currency", settings.get("currency", "IDR"))
    title = "QUOTATION" if kind == "quotation" else "INVOICE"

    # Header table (company left, doc info right)
    header_left = Paragraph(
        f"<b>{company_name}</b><br/>"
        f"<font size='8' color='#555555'>{tagline}</font><br/>"
        f"<font size='8' color='#555555'>{settings.get('company_address','')}</font><br/>"
        f"<font size='8' color='#555555'>{settings.get('company_email','')} | {settings.get('company_phone','')}</font>",
        ss["Body9"],
    )
    doc_info_rows = [
        [Paragraph(f"<b>{title}</b>", ss["TitleBig"])],
        [Paragraph(f"<b>No.</b> {doc.get('number','')}", ss["Body9"])],
        [Paragraph(f"<b>Date</b> {doc.get('date','')}", ss["Body9"])],
    ]
    if kind == "quotation":
        doc_info_rows.append([Paragraph(f"<b>Valid Until</b> {doc.get('valid_until','')}", ss["Body9"])])
    else:
        doc_info_rows.append([Paragraph(f"<b>Due Date</b> {doc.get('due_date','')}", ss["Body9"])])

    doc_info = Table(doc_info_rows, colWidths=[70 * mm])
    doc_info.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))

    header = Table([[header_left, doc_info]], colWidths=[100 * mm, 70 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND_BLACK),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 8 * mm))

    # Bill To
    story.append(Paragraph("BILL TO", ss["Label"]))
    story.append(Paragraph(
        f"<b>{customer.get('company_name','')}</b><br/>"
        f"{customer.get('pic_name','')} — {customer.get('position','')}<br/>"
        f"{customer.get('address','')}<br/>"
        f"{customer.get('email','')} | {customer.get('phone','')}",
        ss["Body9"],
    ))
    story.append(Spacer(1, 6 * mm))

    # Items table
    table_data = [["#", "Item", "Qty", "Unit Price", "Disc %", "Tax %", "Amount"]]
    for i, it in enumerate(doc.get("items", []), 1):
        qty = float(it.get("quantity", 0))
        up = float(it.get("unit_price", 0))
        disc = float(it.get("discount_percent", 0))
        tax = float(it.get("tax_percent", 0))
        line = qty * up * (1 - disc / 100) * (1 + tax / 100)
        name = it.get("product_name", "")
        desc = it.get("description", "")
        cell = f"<b>{name}</b>"
        if desc:
            cell += f"<br/><font size='8' color='#555555'>{desc}</font>"
        table_data.append([
            str(i),
            Paragraph(cell, ss["Body9"]),
            f"{qty:g}",
            _fmt_money(up, currency),
            f"{disc:g}",
            f"{tax:g}",
            _fmt_money(line, currency),
        ])

    items_table = Table(table_data, colWidths=[10 * mm, 60 * mm, 15 * mm, 30 * mm, 15 * mm, 15 * mm, 30 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # Totals
    subtotal, disc_total, tax_total, grand = _compute_totals(doc.get("items", []))
    totals_data = [
        ["Subtotal", _fmt_money(subtotal, currency)],
        ["Discount", "- " + _fmt_money(disc_total, currency)],
        ["Tax", _fmt_money(tax_total, currency)],
        ["TOTAL", _fmt_money(grand, currency)],
    ]
    totals = Table(totals_data, colWidths=[35 * mm, 40 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, BRAND_BLACK),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8 * mm))

    # Notes / footer
    footer_bits = []
    if doc.get("notes"):
        footer_bits.append(f"<b>Notes:</b> {doc.get('notes','')}")
    if doc.get("payment_terms"):
        footer_bits.append(f"<b>Payment Terms:</b> {doc.get('payment_terms','')}")
    if kind == "quotation" and doc.get("delivery_time"):
        footer_bits.append(f"<b>Delivery Time:</b> {doc.get('delivery_time','')}")
    for line in footer_bits:
        story.append(Paragraph(line, ss["Body9"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f"<font size='8' color='#555555'>Generated by {company_name} — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</font>",
        ss["Muted"],
    ))

    pdf.build(story)
    return buf.getvalue()


def build_product_catalog_pdf(products: list, settings: dict) -> bytes:
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    ss = _styles()
    story = [
        Paragraph(f"<b>Product Catalog</b>", ss["TitleBig"]),
        Paragraph(settings.get("company_name", ""), ss["Muted"]),
        Spacer(1, 6 * mm),
    ]
    data = [["Code", "Name", "Type", "Category", "Unit", "Price", "Status"]]
    for p in products:
        data.append([
            p.get("code", ""),
            p.get("name", ""),
            p.get("product_type", ""),
            p.get("category", ""),
            p.get("unit", ""),
            _fmt_money(p.get("selling_price", 0), settings.get("currency", "IDR")),
            p.get("status", ""),
        ])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
    ]))
    story.append(t)
    pdf.build(story)
    return buf.getvalue()
