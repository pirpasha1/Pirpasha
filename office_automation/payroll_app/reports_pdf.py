"""PDF reports: individual salary statements and the attendance report."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from .numwords import amount_in_words
from .payroll import PayrollResult

NAVY = colors.HexColor("#1F3864")
LIGHT = colors.HexColor("#D9E1F2")
STATUS_COLORS = {
    "P": "#C6EFCE", "A": "#FFC7CE", "HD": "#FFEB9C", "L": "#BDD7EE", "LWP": "#F8CBAD",
    "H": "#D9D9D9", "WO": "#EDEDED",
}

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_styles["Title"], fontSize=15, textColor=NAVY, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=_styles["Heading2"], fontSize=10.5, textColor=NAVY, spaceBefore=6, spaceAfter=3)
SMALL = ParagraphStyle("small", parent=_styles["Normal"], fontSize=8, textColor=colors.grey)
NORMAL = ParagraphStyle("n", parent=_styles["Normal"], fontSize=9)
RIGHT = ParagraphStyle("r", parent=NORMAL, alignment=TA_RIGHT)
HDR = ParagraphStyle("hdr", parent=NORMAL, fontName="Helvetica-Bold", fontSize=7.5, leading=8.5,
                     textColor=colors.white, alignment=1)


def _esc(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _m(x: float, cur: str) -> str:
    return f"{cur} {x:,.2f}"


def _grid(data, col_widths, header_rows=1, zebra=True, align_right_from=None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (-1, header_rows - 1), "Helvetica-Bold", 8.5),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if zebra:
        for r in range(header_rows, len(data)):
            if (r - header_rows) % 2:
                style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F2F2F2")))
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, header_rows), (-1, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _footer(company: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.grey)
        w = doc.pagesize[0]
        canvas.drawString(doc.leftMargin, 8 * mm,
                          f"{company} – computer-generated document")
        canvas.drawRightString(w - doc.rightMargin, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _statement_story(result: PayrollResult, emp_id: str) -> list:
    s, cur = result.settings, result.settings.currency
    p = result.payroll[result.payroll["employee_id"] == emp_id]
    if p.empty:
        raise KeyError(f"Employee {emp_id} not found in payroll")
    p = p.iloc[0]
    daily = result.daily[result.daily["employee_id"] == emp_id]
    story: list = [
        Paragraph(_esc(s.company_name), H1),
        Paragraph(f"Salary Statement for <b>{s.period_label}</b> &nbsp;&nbsp; "
                  f"<font size=7 color='grey'>Generated {datetime.now():%d-%b-%Y %H:%M}</font>", NORMAL),
        Spacer(1, 6),
    ]
    info = [
        ["Employee ID", p.employee_id, "Department", p.department],
        ["Name", p["name"], "Designation", p.designation or "-"],
        ["Daily Wage", _m(p.daily_wage, cur), "Bank Account", p.bank_account or "-"],
        ["Wage Basis", p.wage_basis, "Pay Period",
         f"{s.period_start:%d-%b-%Y} to {s.period_end:%d-%b-%Y}"],
    ]
    t = Table([[Paragraph(f"<b>{_esc(a)}</b>", NORMAL), Paragraph(_esc(b), NORMAL),
                Paragraph(f"<b>{_esc(c)}</b>", NORMAL), Paragraph(_esc(d), NORMAL)] for a, b, c, d in info],
              colWidths=[28 * mm, 62 * mm, 28 * mm, 62 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY), ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT), ("BACKGROUND", (2, 0), (2, -1), LIGHT),
    ]))
    story += [t, Paragraph("Attendance Summary", H2)]
    att_hdr = [Paragraph(h, HDR) for h in ("Days in Month", "Present", "Half Days", "Paid Leave",
                                           "Holiday / W.Off", "Absent", "Leave w/o Pay",
                                           "Not Recorded", "Paid Days", "Attend. %")]
    att_row = [p.days_in_month, p.present, p.half_days, p.paid_leave, p.holidays + p.weekly_off,
               p.absent, p.leave_without_pay, p.unrecorded_days, f"{p.paid_days:g}",
               f"{p.attendance_pct:.1f}%"]
    story.append(_grid([att_hdr, att_row], [18 * mm] * 10, zebra=False))

    story.append(Paragraph("Earnings &amp; Deductions", H2))
    earn = [
        ["Earnings", "Amount", "Deductions", "Amount"],
        [f"Wages earned ({p.paid_days:g} paid days x {_m(p.daily_wage, cur)})", _m(p.basic_earnings, cur),
         "Deductions / advances", _m(p.deduction, cur)],
        [f"Overtime ({p.ot_hours:g} h x {s.overtime_multiplier:g} rate)", _m(p.ot_pay, cur), "", ""],
        ["Allowance", _m(p.allowance, cur), "", ""],
        ["Gross Pay", _m(p.gross_pay, cur), "Total Deductions", _m(p.deduction, cur)],
    ]
    t = _grid(earn, [70 * mm, 30 * mm, 50 * mm, 30 * mm], zebra=False)
    t.setStyle(TableStyle([
        ("ALIGN", (1, 1), (1, -1), "RIGHT"), ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8.5), ("BACKGROUND", (0, -1), (-1, -1), LIGHT),
    ]))
    story.append(t)
    net = Table([[Paragraph("<b>NET PAY</b>", NORMAL), Paragraph(f"<b>{_m(p.net_pay, cur)}</b>", RIGHT)],
                 [Paragraph(f"<i>{_esc(amount_in_words(p.net_pay, cur))}</i>", NORMAL), ""]],
                colWidths=[130 * mm, 50 * mm])
    net.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, NAVY), ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("SPAN", (0, 1), (1, 1)), ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    story += [Spacer(1, 6), net, Paragraph("Daily Wage Details", H2)]

    rows = [["Date", "Day", "Status", "Paid", "Day Earning", "OT Hours", "OT Pay", "Total"]]
    for _, d in daily.iterrows():
        rows.append([f"{d.date:%d-%b-%Y}", d.weekday, f"{d.status} – {d.status_label}",
                     f"{d.paid_fraction:g}", f"{d.day_earning:,.2f}",
                     f"{d.ot_hours:g}" if d.ot_hours else "-",
                     f"{d.ot_pay:,.2f}" if d.ot_pay else "-", f"{d.total_earning:,.2f}"])
    if len(rows) == 1:
        rows.append(["No attendance recorded", "", "", "", "", "", "", ""])
    else:
        rows.append(["Total", "", "", f"{daily.paid_fraction.sum():g}", f"{daily.day_earning.sum():,.2f}",
                     f"{daily.ot_hours.sum():g}", f"{daily.ot_pay.sum():,.2f}",
                     f"{daily.total_earning.sum():,.2f}"])
    t = _grid(rows, [24 * mm, 12 * mm, 40 * mm, 12 * mm, 26 * mm, 18 * mm, 22 * mm, 26 * mm],
              align_right_from=3)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 7.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
          ("TOPPADDING", (0, 0), (-1, -1), 0.9), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.9),
          ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 7.5), ("BACKGROUND", (0, -1), (-1, -1), LIGHT)]
    for r, (_, d) in enumerate(daily.iterrows(), start=1):
        st.append(("BACKGROUND", (2, r), (2, r), colors.HexColor(STATUS_COLORS.get(d.status, "#FFFFFF"))))
    t.setStyle(TableStyle(st))
    story.append(t)
    extra = (float(p.ot_hours) - float(daily.ot_hours.sum())) if len(daily) else float(p.ot_hours)
    if extra > 0.0001:
        story.append(Paragraph(f"Includes {extra:g} monthly OT hours recorded on the muster roll.", SMALL))
    sig = Table([["Employee Signature", "", "Authorised Signatory"]],
                colWidths=[60 * mm, 40 * mm, 60 * mm], hAlign="CENTER", spaceBefore=14)
    sig.setStyle(TableStyle([("LINEABOVE", (0, 0), (0, 0), 0.5, colors.black),
                             ("LINEABOVE", (2, 0), (2, 0), 0.5, colors.black),
                             ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 3)]))
    story.append(sig)
    return story


def _doc(buf, pagesize=A4, title="") -> SimpleDocTemplate:
    return SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=14 * mm, rightMargin=14 * mm,
                             topMargin=10 * mm, bottomMargin=14 * mm, title=title, author="Office Automation")


def salary_statement_pdf(result: PayrollResult, emp_id: str) -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, title=f"Salary Statement {emp_id} {result.settings.period_label}")
    doc.build(_statement_story(result, emp_id), onFirstPage=_footer(result.settings.company_name),
              onLaterPages=_footer(result.settings.company_name))
    return buf.getvalue()


def all_statements_pdf(result: PayrollResult, emp_ids: list[str] | None = None) -> bytes:
    """One combined PDF, one employee per page (for printing)."""
    ids = list(result.payroll["employee_id"]) if emp_ids is None else list(emp_ids)
    story: list = []
    for i, emp_id in enumerate(ids):
        if i:
            story.append(PageBreak())
        story += _statement_story(result, emp_id)
    if not story:
        story = [Paragraph("No employees selected.", NORMAL)]
    buf = io.BytesIO()
    doc = _doc(buf, title=f"Salary Statements {result.settings.period_label}")
    doc.build(story, onFirstPage=_footer(result.settings.company_name),
              onLaterPages=_footer(result.settings.company_name))
    return buf.getvalue()


def safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "file"


def statement_filename(result: PayrollResult, emp_id: str) -> str:
    row = result.payroll[result.payroll["employee_id"] == emp_id].iloc[0]
    s = result.settings
    return safe_filename(f"Salary_{emp_id}_{row['name']}_{s.year}-{s.month:02d}") + ".pdf"


def statements_zip(result: PayrollResult, emp_ids: list[str] | None = None) -> bytes:
    """ZIP archive containing one PDF per employee."""
    ids = list(result.payroll["employee_id"]) if emp_ids is None else list(emp_ids)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for emp_id in ids:
            zf.writestr(statement_filename(result, emp_id), salary_statement_pdf(result, emp_id))
    return buf.getvalue()


def attendance_report_pdf(result: PayrollResult, payroll: pd.DataFrame | None = None) -> bytes:
    """Landscape attendance report: summary table + day-wise register."""
    s = result.settings
    pay = result.payroll if payroll is None else payroll
    ids = list(pay["employee_id"])
    summ = result.attendance_summary.set_index("employee_id").loc[ids].reset_index() if ids else \
        result.attendance_summary.iloc[0:0]
    story: list = [Paragraph(_esc(s.company_name), H1),
                   Paragraph(f"Attendance Report – <b>{s.period_label}</b> &nbsp; ({len(ids)} employees)", NORMAL),
                   Paragraph("Summary", H2)]
    hdr = ["ID", "Name", "Department", "Present", "Half", "Leave", "Hol/WO", "Absent", "LWP",
           "Unrec.", "Worked", "Paid", "OT h", "Att. %"]
    rows = [hdr]
    for _, r in summ.iterrows():
        rows.append([r.employee_id, Paragraph(_esc(r["name"]), NORMAL), Paragraph(_esc(r.department), NORMAL),
                     r.present, r.half_days, r.paid_leave, r.holidays + r.weekly_off, r.absent,
                     r.leave_without_pay, r.unrecorded_days, f"{r.worked_days:g}", f"{r.paid_days:g}",
                     f"{r.ot_hours:g}", f"{r.attendance_pct:.1f}%"])
    if len(summ):
        rows.append(["", "Average attendance", "", "", "", "", "", "", "", "", "", "", "",
                     f"{summ.attendance_pct.mean():.1f}%"])
    t = _grid(rows, [18 * mm, 48 * mm, 34 * mm] + [15 * mm] * 10 + [18 * mm], align_right_from=3)
    t.setStyle(TableStyle([("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8.5)]))
    low = [i for i, (_, r) in enumerate(summ.iterrows(), start=1) if r.attendance_pct < 75]
    for i in low:
        t.setStyle(TableStyle([("TEXTCOLOR", (-1, i), (-1, i), colors.red)]))
    story += [t, Paragraph("Attendance below 75% is shown in red.", SMALL), PageBreak(),
              Paragraph("Day-wise Attendance Register", H2),
              Paragraph(" &nbsp; ".join(f"<b>{c.code}</b> = {c.label}" for c in s.status_codes.values()), SMALL),
              Spacer(1, 4)]

    mat = result.attendance_matrix.set_index("employee_id").loc[ids].reset_index() if ids else \
        result.attendance_matrix.iloc[0:0]
    days = [c for c in result.attendance_matrix.columns if isinstance(c, int)]
    rows = [["ID", "Name"] + [str(d) for d in days]]
    for _, r in mat.iterrows():
        rows.append([r.employee_id, _esc(str(r["name"]))[:18]] + [r[d] for d in days])
    day_w = (269 * mm - 16 * mm - 34 * mm) / max(len(days), 1)
    t = Table(rows, colWidths=[16 * mm, 34 * mm] + [day_w] * len(days), repeatRows=1)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 6.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6.5),
          ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BFBFBF")),
          ("ALIGN", (2, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (2, 0), (-1, -1), 0),
          ("RIGHTPADDING", (2, 0), (-1, -1), 0)]
    for ri in range(1, len(rows)):
        for ci in range(2, len(rows[ri])):
            col = STATUS_COLORS.get(rows[ri][ci])
            if col:
                st.append(("BACKGROUND", (ci, ri), (ci, ri), colors.HexColor(col)))
    t.setStyle(TableStyle(st))
    story.append(t)

    buf = io.BytesIO()
    doc = _doc(buf, pagesize=landscape(A4), title=f"Attendance Report {s.period_label}")
    doc.build(story, onFirstPage=_footer(s.company_name), onLaterPages=_footer(s.company_name))
    return buf.getvalue()
