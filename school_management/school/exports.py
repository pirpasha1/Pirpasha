"""PDF (reportlab) and Excel (openpyxl) file builders."""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import COMPETENCY_LEVELS, TERMS
from .services import GRADE_SCALE

HEADER_BG = colors.HexColor("#1f4e79")
ALT_ROW = colors.HexColor("#eef3f8")

_styles = getSampleStyleSheet()
S_TITLE = ParagraphStyle("t", parent=_styles["Title"], fontSize=16, spaceAfter=2, leading=19)
S_SUB = ParagraphStyle("s", parent=_styles["Normal"], alignment=TA_CENTER, fontSize=9, textColor=colors.grey)
S_H2 = ParagraphStyle("h2", parent=_styles["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4,
                      textColor=HEADER_BG)
S_CELL = ParagraphStyle("c", parent=_styles["Normal"], fontSize=8, leading=10)
S_CELL_B = ParagraphStyle("cb", parent=S_CELL, fontName="Helvetica-Bold")
S_SMALL = ParagraphStyle("sm", parent=_styles["Normal"], fontSize=7.5, leading=9, textColor=colors.grey)


def _txt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value == int(value) else f"{value:.1f}"
    return str(value)


def _esc(value):
    return _txt(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _school_header(settings, title, subtitle=None):
    parts = [Paragraph(_esc(settings.get("school_name") or "School"), S_TITLE)]
    line = " | ".join(x for x in (settings.get("school_address"), settings.get("school_phone"),
                                  settings.get("school_email")) if x)
    if line:
        parts.append(Paragraph(_esc(line), S_SUB))
    codes = " | ".join(x for x in (
        f"Affiliation No: {settings['affiliation_no']}" if settings.get("affiliation_no") else "",
        f"UDISE: {settings['udise_code']}" if settings.get("udise_code") else "") if x)
    if codes:
        parts.append(Paragraph(_esc(codes), S_SUB))
    parts.append(Spacer(1, 4))
    parts.append(Paragraph(f"<b>{_esc(title)}</b>", ParagraphStyle("tt", parent=S_SUB, fontSize=12,
                                                                    textColor=colors.black, leading=15)))
    if subtitle:
        parts.append(Paragraph(_esc(subtitle), S_SUB))
    parts.append(Spacer(1, 6))
    return parts


def _grid_style(header_rows=1, zebra=True, font_size=8):
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa9b8")),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    return style + ([("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, ALT_ROW])] if zebra else [])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(doc.leftMargin, 8 * mm, f"Printed on {date.today().strftime('%d-%m-%Y')}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def table_pdf(settings, title, headers, rows, subtitle=None, wide=None, col_widths=None,
              extra=None, font_size=None):
    """Build a simple, printable table report. Returns a BytesIO."""
    buf = BytesIO()
    if wide is None:
        wide = len(headers) > 7
    pagesize = landscape(A4) if wide else A4
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=14 * mm, title=title)
    fs = font_size or (6.5 if len(headers) > 20 else 8)
    cell = ParagraphStyle("cx", parent=S_CELL, fontSize=fs, leading=fs + 2)
    data = [[Paragraph(f"<b>{_esc(h)}</b>", ParagraphStyle("hx", parent=cell, textColor=colors.white))
             for h in headers]]
    for r in rows:
        data.append([Paragraph(_esc(v), cell) for v in r])
    if not rows:
        data.append([Paragraph("No records found.", cell)] + [""] * (len(headers) - 1))
    story = _school_header(settings, title, subtitle)
    if col_widths is None:
        col_widths = _auto_widths(headers, rows, pagesize[0] - 20 * mm, fs)
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle(_grid_style(font_size=fs)))
    story.append(table)
    for item in extra or []:
        story.append(Spacer(1, 6))
        story.append(item)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


def _auto_widths(headers, rows, total, font_size):
    """Share the page width between columns according to their longest text."""
    weights = []
    for i, h in enumerate(headers):
        longest = max([len(_txt(r[i])) for r in rows if i < len(r)] + [min(len(str(h)), 12), 1])
        weights.append(min(longest, 40) + 1.5)
    scale = total / sum(weights)
    return [w * scale for w in weights]


def small_table(headers, rows, col_widths=None):
    data = [[Paragraph(f"<b>{_esc(h)}</b>", ParagraphStyle("h", parent=S_CELL, textColor=colors.white))
             for h in headers]]
    data += [[Paragraph(_esc(v), S_CELL) for v in r] for r in rows]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle(_grid_style()))
    return t


def table_xlsx(settings, title, headers, rows, subtitle=None, sheets=None):
    """Build an Excel workbook. `sheets` may add further (name, headers, rows) sheets."""
    wb = Workbook()
    ws = wb.active
    _fill_sheet(ws, settings, title, headers, rows, subtitle)
    for name, h, r in sheets or []:
        _fill_sheet(wb.create_sheet(), settings, name, h, r, subtitle)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _fill_sheet(ws, settings, title, headers, rows, subtitle=None):
    ws.title = "".join(ch for ch in title if ch not in "[]:*?/\\")[:31] or "Sheet"
    thin = Side(style="thin", color="9AA9B8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ncols = max(len(headers), 1)
    ws.cell(row=1, column=1, value=settings.get("school_name") or "School").font = Font(size=14, bold=True)
    ws.cell(row=2, column=1, value=title).font = Font(size=12, bold=True)
    ws.cell(row=3, column=1, value=subtitle or f"Generated on {date.today().strftime('%d-%m-%Y')}")
    for r in (1, 2, 3):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
    header_row = 5
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    for r_i, row in enumerate(rows, start=header_row + 1):
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=r_i, column=c, value=v)
            cell.border = border
    for c, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(row[c - 1])) for row in rows if c - 1 < len(row) and row[c - 1]
                                     is not None] + [4])
        ws.column_dimensions[get_column_letter(c)].width = min(width + 2, 50)
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.print_title_rows = f"{header_row}:{header_row}"
    ws.page_setup.orientation = "landscape" if ncols > 7 else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0


# ------------------------------------------------------------ report card

def _report_card_story(card, settings):
    s = card["student"]
    k = card["klass"]
    story = _school_header(settings, "PROGRESS REPORT", f"Academic Year {card['year']}")

    info = [
        ["Student Name", s["name"], "Admission No", s["admission_no"]],
        ["Class / Section", f"{k['grade']} - {k['section']}" if k else "-", "Roll No", _txt(s["roll_no"])],
        ["Father's Name", s["father_name"] or "", "Mother's Name", s["mother_name"] or ""],
        ["Date of Birth", _dmy(s["dob"]), "APAAR ID", s["apaar_id"] or ""],
    ]
    t = Table([[Paragraph(f"<b>{_esc(a)}</b>", S_CELL), Paragraph(_esc(b), S_CELL),
                Paragraph(f"<b>{_esc(c)}</b>", S_CELL), Paragraph(_esc(d), S_CELL)] for a, b, c, d in info],
              colWidths=[30 * mm, 65 * mm, 30 * mm, 65 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa9b8")),
                           ("BACKGROUND", (0, 0), (0, -1), ALT_ROW), ("BACKGROUND", (2, 0), (2, -1), ALT_ROW),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story += [t, Paragraph("Part A: Scholastic Areas", S_H2)]

    exams = card["exams"]
    head = ["Subject"] + [f"{e['name']} ({_txt(e['max_marks'])})" for e in exams] + ["Total", "%", "Grade"]
    data = [head]
    for r in card["rows"]:
        data.append([r["subject"]["name"]] + [_txt(c) for c in r["cells"]] +
                    [f"{_txt(r['total'])}/{_txt(r['max_total'])}" if r["max_total"] else "",
                     _txt(r["pct"]), r["grade"]])
    data.append(["Overall"] + [""] * len(exams) +
                [f"{_txt(card['total'])}/{_txt(card['max_total'])}" if card["max_total"] else "",
                 _txt(card["pct"]), card["grade"]])
    sub_w = 38 * mm
    rest = (190 * mm - sub_w) / (len(exams) + 3)
    s_head = ParagraphStyle("hw", parent=S_CELL_B, textColor=colors.white)

    def style_for(i, j):
        if i == 0:
            return s_head
        return S_CELL_B if j == 0 or i == len(data) - 1 else S_CELL

    t = Table([[Paragraph(_esc(c), style_for(i, j)) for j, c in enumerate(row)]
               for i, row in enumerate(data)], colWidths=[sub_w] + [rest] * (len(exams) + 3), repeatRows=1)
    t.setStyle(TableStyle(_grid_style() + [("BACKGROUND", (0, -1), (-1, -1), ALT_ROW)]))
    story.append(t)

    summary = [["Result", card["result"] or "-", "Rank in Class",
                f"{card['rank']} of {card['class_size']}" if card["rank"] else "-"],
               ["Attendance", _attendance_txt(card["attendance"]), "Overall Grade", card["grade"] or "-"]]
    t = Table([[Paragraph(f"<b>{_esc(a)}</b>", S_CELL), Paragraph(_esc(b), S_CELL),
                Paragraph(f"<b>{_esc(c)}</b>", S_CELL), Paragraph(_esc(d), S_CELL)] for a, b, c, d in summary],
              colWidths=[30 * mm, 65 * mm, 30 * mm, 65 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa9b8")),
                           ("BACKGROUND", (0, 0), (0, -1), ALT_ROW), ("BACKGROUND", (2, 0), (2, -1), ALT_ROW)]))
    story += [Spacer(1, 4), t]

    story.append(Paragraph("Part B: Co-Scholastic Areas &amp; Life Skills", S_H2))
    rows = [[i["indicator"]["name"], i["indicator"]["area"]] + i["grades"] for i in card["indicators"]]
    story.append(small_table(["Indicator", "Area"] + TERMS, rows, [70 * mm, 40 * mm, 40 * mm, 40 * mm]))
    story.append(Paragraph("Grades: A = Outstanding, B = Very Good, C = Good, D = Needs Improvement", S_SMALL))

    if card["competencies"]:
        story.append(Paragraph("Part C: Learning Outcomes / Competencies", S_H2))
        rows = [[c["subject"], c["code"] or "", c["description"]] +
                [COMPETENCY_LEVELS.get(lv, "") if lv else "" for lv in c["levels"]] for c in card["competencies"]]
        story.append(small_table(["Subject", "Code", "Learning Outcome"] + TERMS, rows,
                                 [28 * mm, 16 * mm, 86 * mm, 30 * mm, 30 * mm]))

    story.append(Paragraph("Class Teacher's Remarks", S_H2))
    rows = [[t_, r or ""] for t_, r in zip(TERMS, card["remarks"])]
    story.append(small_table(["Term", "Remarks"], rows, [30 * mm, 160 * mm]))

    scale = " | ".join(f"{g}: {rng}" for rng, g in GRADE_SCALE)
    story += [Spacer(1, 4), Paragraph(f"Grading scale (marks %): {scale}", S_SMALL), Spacer(1, 26)]
    sig = Table([["Class Teacher", "Principal", "Parent / Guardian"]], colWidths=[63 * mm] * 3)
    sig.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                             ("LINEABOVE", (0, 0), (0, 0), 0.6, colors.black),
                             ("LINEABOVE", (1, 0), (1, 0), 0.6, colors.black),
                             ("LINEABOVE", (2, 0), (2, 0), 0.6, colors.black)]))
    story.append(KeepTogether(sig))
    return story


def _dmy(value):
    if not value:
        return ""
    try:
        y, m, d = str(value)[:10].split("-")
        return f"{d}-{m}-{y}"
    except ValueError:
        return str(value)


def _attendance_txt(att):
    if not att["total"]:
        return "-"
    return f"{att['present']} / {att['total']} days ({att['pct']}%)"


def report_cards_pdf(cards, settings):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=14 * mm, title="Report Card")
    story = []
    for i, card in enumerate(cards):
        if i:
            story.append(PageBreak())
        story += _report_card_story(card, settings)
    if not story:
        story = [Paragraph("No students found.", S_CELL)]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf
