"""Command-line batch mode – process files and write every report to a folder.

Example::

    python -m payroll_app.cli sample_data/*.xlsx --month 2026-10 --out reports
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .importer import import_files
from .payroll import compute_payroll
from .reports_excel import build_consolidated_workbook
from .reports_pdf import attendance_report_pdf, salary_statement_pdf, statement_filename


def _period(text: str) -> tuple[int, int]:
    try:
        y, m = text.split("-")
        y, m = int(y), int(m)
        if not 1 <= m <= 12:
            raise ValueError
        return y, m
    except ValueError:
        raise argparse.ArgumentTypeError("use YYYY-MM, e.g. 2026-10") from None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Payroll & attendance reports from Excel files")
    ap.add_argument("files", nargs="+", type=Path, help="Excel files (.xlsx/.xlsm/.xls)")
    ap.add_argument("--month", required=True, type=_period, help="pay period as YYYY-MM")
    ap.add_argument("--out", type=Path, default=Path("reports"), help="output folder (default: reports)")
    ap.add_argument("--company", default="My Company Pvt. Ltd.")
    ap.add_argument("--currency", default="Rs.")
    ap.add_argument("--divisor", default="calendar",
                    help="monthly salary divisor: 'calendar' (days in month) or a number such as 26")
    ap.add_argument("--hours", type=float, default=8.0, help="standard hours per day (default 8)")
    ap.add_argument("--ot-rate", type=float, default=2.0, help="overtime multiplier (default 2.0)")
    ap.add_argument("--no-pdf", action="store_true", help="skip individual salary statement PDFs")
    a = ap.parse_args(argv)

    try:
        divisor = a.divisor if a.divisor == "calendar" else int(a.divisor)
        s = Settings(company_name=a.company, year=a.month[0], month=a.month[1], currency=a.currency,
                     monthly_divisor=divisor, standard_hours=a.hours, overtime_multiplier=a.ot_rate)
    except ValueError as exc:
        ap.error(str(exc))

    data = import_files(a.files, s)
    order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    for i in sorted(data.issues.issues, key=lambda x: order[x.severity]):
        where = " / ".join(x for x in (i.file, i.sheet, f"row {i.row}" if i.row else "") if x)
        emp = f" [{i.employee_id}]" if i.employee_id else ""
        print(f"{i.severity:7} {where}{emp}: {i.message}", file=sys.stderr)
    if data.employees.empty:
        print("No valid employee records – nothing to report.", file=sys.stderr)
        return 1

    result = compute_payroll(data, s)
    a.out.mkdir(parents=True, exist_ok=True)
    tag = f"{s.year}-{s.month:02d}"
    xlsx = a.out / f"Payroll_Report_{tag}.xlsx"
    xlsx.write_bytes(build_consolidated_workbook(result, data.issues))
    att = a.out / f"Attendance_Report_{tag}.pdf"
    att.write_bytes(attendance_report_pdf(result))
    n = 0
    if not a.no_pdf:
        folder = a.out / f"Salary_Statements_{tag}"
        folder.mkdir(exist_ok=True)
        for emp_id in result.payroll["employee_id"]:
            (folder / statement_filename(result, emp_id)).write_bytes(salary_statement_pdf(result, emp_id))
            n += 1
    t = result.totals
    print(f"\n{s.company_name} – {s.period_label}")
    print(f"  Employees: {t['employees']}   Gross: {s.currency} {t['gross_pay']:,.2f}   "
          f"Net: {s.currency} {t['net_pay']:,.2f}   Avg attendance: {t['avg_attendance']}%")
    print(f"  Errors: {data.issues.count('ERROR')}   Warnings: {data.issues.count('WARNING')}")
    print(f"  Written: {xlsx}\n           {att}" + (f"\n           {n} salary statements in {folder}" if n else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
