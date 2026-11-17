"""Consolidated, formatted Excel workbook."""
from __future__ import annotations

import io
from datetime import date, datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .payroll import PayrollResult
from .validation import IssueLog

HEADERS = {
    "employee_id": "Employee ID", "name": "Name", "department": "Department",
    "designation": "Designation", "wage_basis": "Wage Basis", "daily_wage": "Daily Wage",
    "monthly_salary": "Monthly Salary", "days_in_month": "Days in Month",
    "recorded_days": "Days Recorded", "present": "Present", "half_days": "Half Days",
    "paid_leave": "Paid Leave", "holidays": "Holidays", "weekly_off": "Weekly Off",
    "absent": "Absent", "leave_without_pay": "Leave w/o Pay", "unrecorded_days": "Unrecorded",
    "worked_days": "Days Worked", "paid_days": "Paid Days", "attendance_pct": "Attendance %",
    "ot_hours": "OT Hours", "basic_earnings": "Wages Earned", "ot_pay": "OT Pay",
    "allowance": "Allowance", "gross_pay": "Gross Pay", "deduction": "Deductions",
    "net_pay": "Net Pay", "bank_account": "Bank Account", "date": "Date", "weekday": "Day",
    "status": "Status", "status_label": "Status Description", "paid_fraction": "Paid Fraction",
    "worked_fraction": "Worked Fraction", "day_earning": "Day Earning",
    "total_earning": "Total Earning", "employees": "Employees",
    "avg_attendance_pct": "Avg Attendance %", "source": "Source (file / sheet / row)",
    "severity": "Severity", "message": "Message", "file": "File", "sheet": "Sheet", "row": "Row",
}
MONEY = {"daily_wage", "monthly_salary", "basic_earnings", "ot_pay", "allowance", "gross_pay",
         "deduction", "net_pay", "day_earning", "total_earning"}
DECIMAL = {"worked_days", "paid_days", "ot_hours", "paid_fraction", "worked_fraction"}
PERCENT = {"attendance_pct", "avg_attendance_pct"}
SUM_COLS = MONEY - {"daily_wage", "monthly_salary"} | {"paid_days", "worked_days", "ot_hours",
                                                       "present", "absent", "employees"}

NAVY = "1F3864"
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="D9E1F2")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
STATUS_FILLS = {
    "P": "C6EFCE", "A": "FFC7CE", "HD": "FFEB9C", "L": "BDD7EE", "LWP": "F8CBAD",
    "H": "D9D9D9", "WO": "EDEDED",
}
SEVERITY_FILLS = {"ERROR": "FFC7CE", "WARNING": "FFEB9C", "INFO": "DDEBF7"}


def _title(ws: Worksheet, title: str, subtitle: str, width: int) -> int:
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=14, color=NAVY)
    ws.cell(row=2, column=1, value=subtitle).font = Font(italic=True, color="595959")
    if width > 1:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(width, 12))
    return 4  # first row for the table


def _write_table(ws: Worksheet, df: pd.DataFrame, start_row: int, currency: str,
                 totals: bool = False, freeze: bool = True) -> int:
    cols = list(df.columns)
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=start_row, column=j, value=HEADERS.get(str(c), str(c)))
        cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    money_fmt = f'"{currency}" #,##0.00' if currency else "#,##0.00"
    for i, rec in enumerate(df.itertuples(index=False), start=start_row + 1):
        for j, (c, v) in enumerate(zip(cols, rec), start=1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            elif v is pd.NA:
                v = None
            cell = ws.cell(row=i, column=j, value=v)
            cell.border = BORDER
            if c in MONEY:
                cell.number_format = money_fmt
            elif c in DECIMAL:
                cell.number_format = "0.0#"
            elif c in PERCENT:
                cell.number_format = '0.0"%"'
            elif c == "date" or isinstance(v, (date, datetime)):
                cell.number_format = "DD-MMM-YYYY"
    last = start_row + len(df)
    if totals and len(df):
        last += 1
        ws.cell(row=last, column=1, value="TOTAL")
        for j, c in enumerate(cols, start=1):
            cell = ws.cell(row=last, column=j)
            cell.fill, cell.font, cell.border = TOTAL_FILL, Font(bold=True), BORDER
            if c in SUM_COLS and pd.api.types.is_numeric_dtype(df[c]):
                cell.value = round(float(df[c].sum()), 2)
                cell.number_format = money_fmt if c in MONEY else "0.0#"
    # widths
    for j, c in enumerate(cols, start=1):
        header = HEADERS.get(str(c), str(c))
        sample = df[c].head(200).map(lambda v: len(str(v))).max() if len(df) else 0
        width = min(max(len(header), int(sample or 0)) + 3, 45)
        if c in MONEY:
            width = max(width, 14)
        ws.column_dimensions[get_column_letter(j)].width = max(width, 6)
    ws.row_dimensions[start_row].height = 30
    if freeze:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=3 if "name" in cols else 1)
    if len(df):
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(cols))}{start_row + len(df)}"
    return last


def build_consolidated_workbook(result: PayrollResult, import_issues: IssueLog | None = None,
                                payroll: pd.DataFrame | None = None) -> bytes:
    """Return the consolidated report as ``.xlsx`` bytes.

    ``payroll`` may be a filtered subset; all other sheets are restricted to the
    same employees so the workbook is consistent.
    """
    s = result.settings
    cur = s.currency
    pay = result.payroll if payroll is None else payroll
    ids = set(pay["employee_id"])
    sub = f"{s.company_name}  |  Pay period: {s.period_label}  |  Generated {datetime.now():%d-%b-%Y %H:%M}"

    wb = Workbook()
    # ---- Summary --------------------------------------------------------
    ws = wb.active
    ws.title = "Summary"
    _title(ws, f"Payroll Summary – {s.period_label}", sub, 8)
    from .payroll import department_summary  # local import avoids cycle at module load
    t = {
        "Employees": len(pay),
        "Total Gross Pay": round(float(pay["gross_pay"].sum()), 2) if len(pay) else 0,
        "Total Overtime Pay": round(float(pay["ot_pay"].sum()), 2) if len(pay) else 0,
        "Total Deductions": round(float(pay["deduction"].sum()), 2) if len(pay) else 0,
        "Total Net Pay": round(float(pay["net_pay"].sum()), 2) if len(pay) else 0,
        "Average Attendance %": round(float(pay["attendance_pct"].mean()), 1) if len(pay) else 0,
    }
    row = 4
    for k, v in t.items():
        ws.cell(row=row, column=1, value=k).font = Font(bold=True)
        c = ws.cell(row=row, column=2, value=v)
        if "Pay" in k or "Deduction" in k:
            c.number_format = f'"{cur}" #,##0.00'
        elif "%" in k:
            c.number_format = '0.0"%"'
        row += 1
    rules = [
        f"Daily wage: from 'Daily Wage' column, or Monthly Salary / "
        f"{'days in the month' if s.monthly_divisor == 'calendar' else f'{s.monthly_divisor} days'}",
        f"Overtime: OT hours x (daily wage / {s.standard_hours:g} h) x {s.overtime_multiplier:g}",
        "Gross = wages earned + OT pay + allowance;  Net = gross - deductions",
        "Paid status codes: " + ", ".join(f"{c.code}={c.label} ({c.paid:g})" for c in s.status_codes.values()),
    ]
    row += 1
    ws.cell(row=row, column=1, value="Calculation rules").font = Font(bold=True, color=NAVY)
    for r in rules:
        row += 1
        ws.cell(row=row, column=1, value=r)
    row += 2
    ws.cell(row=row, column=1, value="Department summary").font = Font(bold=True, color=NAVY)
    _write_table(ws, department_summary(pay), row + 1, cur, totals=True, freeze=False)
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 18

    # ---- Salary register -------------------------------------------------
    ws = wb.create_sheet("Salary Register")
    start = _title(ws, f"Salary Register – {s.period_label}", sub, 12)
    _write_table(ws, pay, start, cur, totals=True)

    # ---- Attendance summary ---------------------------------------------
    ws = wb.create_sheet("Attendance Summary")
    start = _title(ws, f"Attendance Report – {s.period_label}", sub, 12)
    att = result.attendance_summary[result.attendance_summary["employee_id"].isin(ids)]
    _write_table(ws, att.reset_index(drop=True), start, cur, totals=True)

    # ---- Attendance matrix ----------------------------------------------
    ws = wb.create_sheet("Attendance Register")
    start = _title(ws, f"Attendance Register (day-wise) – {s.period_label}",
                   sub + "  |  " + ", ".join(f"{c.code}={c.label}" for c in s.status_codes.values()), 12)
    mat = result.attendance_matrix[result.attendance_matrix["employee_id"].isin(ids)].reset_index(drop=True)
    last = _write_table(ws, mat, start, cur)
    ncols = len(mat.columns)
    for j, c in enumerate(mat.columns, start=1):
        if isinstance(c, int):
            ws.column_dimensions[get_column_letter(j)].width = 5
            d = date(s.year, s.month, c)
            ws.cell(row=start, column=j).value = f"{c}\n{d:%a}"
    for r in range(start + 1, last + 1):
        for j in range(4, ncols + 1):
            cell = ws.cell(row=r, column=j)
            cell.alignment = Alignment(horizontal="center")
            if cell.value in STATUS_FILLS:
                cell.fill = PatternFill("solid", fgColor=STATUS_FILLS[cell.value])

    # ---- Daily wages -----------------------------------------------------
    ws = wb.create_sheet("Daily Wages")
    start = _title(ws, f"Daily Wage Calculation – {s.period_label}", sub, 12)
    daily = result.daily[result.daily["employee_id"].isin(ids)].reset_index(drop=True)
    _write_table(ws, daily, start, cur, totals=True)

    # ---- Employees -------------------------------------------------------
    ws = wb.create_sheet("Employees")
    start = _title(ws, "Employee Master (as imported)", sub, 10)
    emp = result.employees[result.employees["employee_id"].isin(ids)].reset_index(drop=True)
    _write_table(ws, emp, start, cur)

    # ---- Validation ------------------------------------------------------
    ws = wb.create_sheet("Validation Issues")
    start = _title(ws, "Data Validation Log", sub, 6)
    log = IssueLog()
    if import_issues is not None:
        log.extend(import_issues)
    log.extend(result.issues)
    issues = log.to_frame()
    last = _write_table(ws, issues, start, cur, freeze=False)
    for r in range(start + 1, last + 1):
        sev = ws.cell(row=r, column=1).value
        if sev in SEVERITY_FILLS:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=SEVERITY_FILLS[sev])
    ws.column_dimensions["B"].width = 90
    if issues.empty:
        ws.cell(row=start + 1, column=1, value="No issues found – all data passed validation.")

    for sheet in wb.worksheets:
        sheet.sheet_view.zoomScale = 90
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.print_title_rows = None

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
