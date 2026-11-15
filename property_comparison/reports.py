"""Side-by-side comparison table plus PDF and Excel report generation."""
import io
from datetime import datetime

from . import formatting as fmt
from .models import photo_path, type_summary

# (label, property key, kind, which value is "best": "min", "max", "true" or None)
COMPARISON_ROWS = [
    ("Type", "property_type", "text", None),
    ("Locality", "locality", "text", None),
    ("City", "city", "text", None),
    ("Price", "price", "inr", "min"),
    ("Carpet / plot area", "carpet_area_sqft", "sqft", "max"),
    ("Price per sq ft", "price_per_sqft", "inr", "min"),
    ("BHK", "bhk", "int", None),
    ("Floor", "floor_display", "text", None),
    ("Facing", "facing", "text", None),
    ("Ready to move", "ready_to_move", "bool", "true"),
    ("Possession date", "possession_date", "text", None),
    ("Developer", "developer", "text", None),
    ("Railway station", "railway_station_name", "text", None),
    ("Railway station distance", "railway_station_km", "km", "min"),
    ("Bus stand", "bus_stand_name", "text", None),
    ("Bus stand distance", "bus_stand_km", "km", "min"),
    ("Highway", "highway_name", "text", None),
    ("Highway distance", "highway_km", "km", "min"),
    ("Connectivity notes", "connectivity_notes", "text", None),
    ("Amenities", "amenities", "text", None),
]


def format_value(kind, value, symbol="₹"):
    if kind == "bool":
        return fmt.yes_no(value)
    if value is None or value == "":
        return "—"
    if kind == "inr":
        return fmt.inr(value, symbol)
    if kind == "sqft":
        return fmt.sqft(value)
    if kind == "km":
        return fmt.km(value)
    return str(value)


def comparison_rows(props):
    """Rows for the comparison grid with the indices of the best value(s) marked.

    A row only gets a highlight when at least two properties have a value and
    they are not all equal, so a lone or tied value is never called "best".
    """
    rows = []
    for label, key, kind, best in COMPARISON_ROWS:
        values = [p.get(key) for p in props]
        if all(v in (None, "") for v in values) and kind != "bool":
            continue  # nothing to show for this attribute
        best_idx = set()
        present = [(i, v) for i, v in enumerate(values) if v not in (None, "")]
        if best and len(present) >= 2 and len({v for _, v in present}) > 1:
            if best == "true":
                best_idx = {i for i, v in present if v}
            else:
                target = (min if best == "min" else max)(v for _, v in present)
                best_idx = {i for i, v in present if v == target}
        rows.append({"label": label, "key": key, "kind": kind, "values": values, "best": best_idx})
    return rows


def _report_title(props):
    return "Property comparison report" if len(props) > 1 else "Property report"


# --------------------------------------------------------------------------- PDF

def build_pdf(props, subtitle=""):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    buf = io.BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(buf, pagesize=page, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title=_report_title(props))
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10,
                          alignment=TA_LEFT)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    label_style = ParagraphStyle("label", parent=cell, fontName="Helvetica-Bold")
    green = colors.HexColor("#d6f5df")
    navy = colors.HexColor("#1f3a5f")

    story = [
        Paragraph(_report_title(props), styles["Title"]),
        Paragraph(f"Generated {datetime.now():%d %b %Y, %H:%M} &middot; "
                  f"{len(props)} propert{'y' if len(props) == 1 else 'ies'}", styles["Normal"]),
    ]
    if subtitle:
        story.append(Paragraph(_esc(subtitle), styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    if not props:
        story.append(Paragraph("No properties match the selection.", styles["Normal"]))
        doc.build(story)
        return buf.getvalue()

    # Type summary (flats vs plots)
    summary = type_summary(props)
    if summary:
        data = [[Paragraph(h, head) for h in
                 ("Type", "Count", "Avg price", "Avg area", "Avg price / sq ft",
                  "Lowest price / sq ft")]]
        for s in summary:
            data.append([Paragraph(x, cell) for x in (
                s["type"], str(s["count"]), fmt.inr(s["avg_price"], "Rs. "),
                fmt.sqft(s["avg_area"]), fmt.inr(s["avg_ppsf"], "Rs. "),
                fmt.inr(s["min_ppsf"], "Rs. "))])
        t = Table(data, hAlign="LEFT", colWidths=[30 * mm, 18 * mm, 40 * mm, 35 * mm, 40 * mm, 40 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2cc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story += [Paragraph("Flats vs plots", styles["Heading3"]), t, Spacer(1, 5 * mm)]

    # Side-by-side comparison, four properties per table so columns stay readable.
    usable = page[0] - doc.leftMargin - doc.rightMargin
    label_w = 42 * mm
    per_table = 4
    chunks = [props[i:i + per_table] for i in range(0, len(props), per_table)]
    for n, chunk in enumerate(chunks):
        col_w = (usable - label_w) / per_table
        rows = comparison_rows(chunk)
        data = [[Paragraph("Attribute", head)] +
                [Paragraph(_esc(p["title"]), head) for p in chunk]]
        photo_row = [Paragraph("Photo", label_style)]
        has_photo = False
        for p in chunk:
            img = _pdf_image(p, col_w - 4 * mm, 32 * mm, Image)
            has_photo = has_photo or img is not None
            photo_row.append(img or Paragraph("No photo", cell))
        if has_photo:
            data.append(photo_row)
        first_value_row = len(data)
        for r in rows:
            data.append([Paragraph(r["label"], label_style)] +
                        [Paragraph(_esc(format_value(r["kind"], v, "Rs. ")), cell)
                         for v in r["values"]])
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#eef2f6")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2cc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for ri, r in enumerate(rows):
            for ci in r["best"]:
                y = first_value_row + ri
                style.append(("BACKGROUND", (ci + 1, y), (ci + 1, y), green))
        t = Table(data, colWidths=[label_w] + [col_w] * len(chunk), repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle(style))
        heading = "Side-by-side comparison"
        if len(chunks) > 1:
            heading += f" ({n + 1} of {len(chunks)})"
        story += [Paragraph(heading, styles["Heading3"]), t]
        if len(props) > 1:
            story.append(Paragraph(
                "Green cells mark the best value in each row among the properties shown "
                "(lowest price and distances, largest area, ready to move).", cell))
        if n < len(chunks) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()


def _pdf_image(prop, max_w, max_h, Image):
    if not prop["photos"]:
        return None
    path = photo_path(prop["photos"][0]["filename"])
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            w, h = im.size
    except OSError:
        return None
    scale = min(max_w / w, max_h / h)
    return Image(path, width=w * scale, height=h * scale)


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------- Excel

INR_FORMAT = '[>=10000000]"₹"##\\,##\\,##\\,##0;[>=100000]"₹"##\\,##\\,##0;"₹"##,##0'


def build_excel(props, subtitle=""):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    bold = Font(bold=True)
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F3A5F")
    label_fill = PatternFill("solid", fgColor="EEF2F6")
    best_fill = PatternFill("solid", fgColor="D6F5DF")
    thin = Side(style="thin", color="B8C2CC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")

    # ---- Comparison sheet: attributes down, properties across
    ws = wb.active
    ws.title = "Comparison"
    ws["A1"] = _report_title(props)
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Generated {datetime.now():%d %b %Y, %H:%M}" + (f" — {subtitle}" if subtitle else "")
    header_row = 4
    ws.cell(header_row, 1, "Attribute")
    for ci, p in enumerate(props, start=2):
        ws.cell(header_row, ci, p["title"])
    for c in ws[header_row]:
        c.font, c.fill, c.alignment, c.border = head_font, head_fill, wrap, border

    r = header_row + 1
    if any(p["photos"] for p in props):
        ws.cell(r, 1, "Photo")
        ws.row_dimensions[r].height = 100
        for ci, p in enumerate(props, start=2):
            if p["photos"]:
                img = _xl_image(p, XLImage)
                if img is not None:
                    ws.add_image(img, f"{get_column_letter(ci)}{r}")
        r += 1

    for row in comparison_rows(props):
        ws.cell(r, 1, row["label"])
        for ci, v in enumerate(row["values"], start=2):
            c = ws.cell(r, ci)
            if row["kind"] == "bool":
                c.value = fmt.yes_no(v)
            elif v in (None, ""):
                c.value = "—"
            else:
                c.value = v
                if row["kind"] == "inr":
                    c.number_format = INR_FORMAT
                elif row["kind"] == "sqft":
                    c.number_format = '#,##0" sq ft"'
                elif row["kind"] == "km":
                    c.number_format = '0.0" km"'
            if (ci - 2) in row["best"]:
                c.fill = best_fill
        r += 1

    for row in ws.iter_rows(min_row=header_row + 1, max_row=r - 1, max_col=len(props) + 1):
        for c in row:
            c.border = border
            c.alignment = wrap
        row[0].font, row[0].fill = bold, label_fill
    ws.column_dimensions["A"].width = 26
    for ci in range(2, len(props) + 2):
        ws.column_dimensions[get_column_letter(ci)].width = 30
    ws.freeze_panes = ws.cell(header_row + 1, 2)
    if len(props) > 1:
        ws.cell(r + 1, 1, "Green cells mark the best value in each row "
                          "(lowest price and distances, largest area, ready to move).").font = \
            Font(italic=True, color="555555")

    # ---- Listings sheet: one row per property, price/sq ft as a live formula
    ls = wb.create_sheet("Listings")
    cols = [
        ("ID", "id", None), ("Title", "title", None), ("Type", "property_type", None),
        ("Locality", "locality", None), ("City", "city", None),
        ("Price (₹)", "price", INR_FORMAT), ("Carpet / plot area (sq ft)", "carpet_area_sqft", "#,##0"),
        ("Price per sq ft (₹)", None, INR_FORMAT), ("BHK", "bhk", None),
        ("Floor", "floor", None), ("Total floors", "total_floors", None), ("Facing", "facing", None),
        ("Ready to move", "ready_to_move", None), ("Possession date", "possession_date", None),
        ("Developer", "developer", None),
        ("Railway station", "railway_station_name", None), ("Railway (km)", "railway_station_km", "0.0"),
        ("Bus stand", "bus_stand_name", None), ("Bus stand (km)", "bus_stand_km", "0.0"),
        ("Highway", "highway_name", None), ("Highway (km)", "highway_km", "0.0"),
        ("Connectivity notes", "connectivity_notes", None), ("Amenities", "amenities", None),
        ("Address", "address", None), ("Notes", "notes", None), ("Photos", None, None),
    ]
    for ci, (title, _, _) in enumerate(cols, start=1):
        c = ls.cell(1, ci, title)
        c.font, c.fill, c.alignment, c.border = head_font, head_fill, wrap, border
    price_col = get_column_letter(6)
    area_col = get_column_letter(7)
    for ri, p in enumerate(props, start=2):
        for ci, (title, key, numfmt) in enumerate(cols, start=1):
            c = ls.cell(ri, ci)
            if title.startswith("Price per sq ft"):
                c.value = f"=IFERROR({price_col}{ri}/{area_col}{ri},\"\")"
            elif title == "Photos":
                c.value = len(p["photos"])
            elif key == "ready_to_move":
                c.value = fmt.yes_no(p[key])
            else:
                c.value = p.get(key)
            if numfmt:
                c.number_format = numfmt
            c.border = border
    widths = [6, 30, 8, 18, 12, 16, 14, 16, 6, 6, 8, 11, 10, 13, 20, 18, 10, 18, 10, 22, 10, 30, 30, 30, 30, 8]
    for ci, w in enumerate(widths, start=1):
        ls.column_dimensions[get_column_letter(ci)].width = w
    ls.freeze_panes = "C2"
    if props:
        ls.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(props) + 1}"

    # ---- Summary sheet: flats vs plots, computed from the Listings sheet so
    #      edits there flow through.
    ss = wb.create_sheet("Flats vs Plots")
    headers = ["Type", "Count", "Avg price (₹)", "Avg area (sq ft)",
               "Avg price per sq ft (₹)", "Lowest price per sq ft (₹)"]
    for ci, h in enumerate(headers, start=1):
        c = ss.cell(1, ci, h)
        c.font, c.fill, c.alignment, c.border = head_font, head_fill, wrap, border
    last = max(len(props) + 1, 2)
    t_rng, p_rng = f"Listings!$C$2:$C${last}", f"Listings!$F$2:$F${last}"
    a_rng, s_rng = f"Listings!$G$2:$G${last}", f"Listings!$H$2:$H${last}"
    for ri, t in enumerate(("Flat", "Plot"), start=2):
        ss.cell(ri, 1, t).font = bold
        ss.cell(ri, 2, f'=COUNTIF({t_rng},A{ri})')
        ss.cell(ri, 3, f'=IFERROR(AVERAGEIF({t_rng},A{ri},{p_rng}),"")').number_format = INR_FORMAT
        ss.cell(ri, 4, f'=IFERROR(AVERAGEIF({t_rng},A{ri},{a_rng}),"")').number_format = "#,##0"
        ss.cell(ri, 5, f'=IFERROR(AVERAGEIF({t_rng},A{ri},{s_rng}),"")').number_format = INR_FORMAT
        ss.cell(ri, 6, f'=IFERROR(_xlfn.MINIFS({s_rng},{t_rng},A{ri}),"")').number_format = INR_FORMAT
        for ci in range(1, 7):
            ss.cell(ri, ci).border = border
    for ci, w in enumerate([10, 8, 18, 16, 22, 24], start=1):
        ss.column_dimensions[get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _xl_image(prop, XLImage):
    from PIL import Image as PILImage
    try:
        with PILImage.open(photo_path(prop["photos"][0]["filename"])) as im:
            im = im.convert("RGB")
            im.thumbnail((200, 130))
            out = io.BytesIO()
            im.save(out, "PNG")
    except OSError:
        return None
    out.seek(0)
    return XLImage(out)
