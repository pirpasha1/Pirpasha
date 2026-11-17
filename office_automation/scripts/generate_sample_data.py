"""Generate realistic sample Excel files (October 2026) for testing / demos.

The files deliberately use *different layouts* and contain a handful of data
errors so the validation features can be seen in action:

* ``employees_master.xlsx``        – two sheets, title rows above the header,
  daily-wage and monthly-salary staff, plus bad rows (negative wage, text wage,
  conflicting duplicate ID, blank name).
* ``attendance_production_oct.xlsx`` – long register format with OT hours,
  plus an unknown status code, a bad date, an unknown employee, a duplicate
  entry and an excessive OT value.
* ``muster_roll_office_oct.xlsx``  – wide muster roll (days 1-31) with a
  monthly OT total column.
* ``contract_staff_oct.xlsx``      – muster roll that also carries the wage, so
  it acts as both employee list and attendance.

Usage:  python scripts/generate_sample_data.py [output_dir]
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

YEAR, MONTH, DAYS = 2026, 10, 31
HOLIDAYS = {2}  # 2 Oct – public holiday

PRODUCTION = [
    ("E001", "Ravi Kumar", "Production", "Machine Operator", 750, 500, 0, "30012345678"),
    ("E002", "Sunita Devi", "Production", "Helper", 600, 300, 200, "30012345679"),
    ("E003", "Mohammed Irfan", "Production", "Supervisor", 1100, 1000, 0, "30012345680"),
    ("E004", "Lakshmi Narayan", "Production", "Machine Operator", 750, 500, 1000, "30012345681"),
    ("E005", "Anil Sharma", "Production", "Welder", 900, 500, 0, "30012345682"),
    ("E006", "Priya Patil", "Quality", "QC Inspector", 850, 400, 0, "30012345683"),
    ("E007", "Joseph Mathew", "Quality", "QC Inspector", 850, 400, 500, "30012345684"),
    ("E008", "Kavita Rao", "Stores", "Store Keeper", 700, 300, 0, "30012345685"),
]
OFFICE = [  # monthly salary staff
    ("M101", "Deepa Iyer", "Accounts", "Accountant", 32000, 2000, 1800, "40011112222"),
    ("M102", "Rahul Verma", "Accounts", "Accounts Assistant", 22000, 1000, 1200, "40011112223"),
    ("M103", "Fatima Shaikh", "Administration", "Office Manager", 45000, 3000, 2500, "40011112224"),
    ("M104", "Vikram Singh", "Administration", "Clerk", 18000, 800, 0, "40011112225"),
    ("M105", "Neha Gupta", "HR", "HR Executive", 28000, 1500, 1500, "40011112226"),
]
CONTRACT = [
    ("C201", "Suresh Yadav", "Loading", "Loader", 550),
    ("C202", "Ramesh Pawar", "Loading", "Loader", 550),
    ("C203", "Geeta Bai", "Housekeeping", "Cleaner", 500),
    ("C204", "Manoj Tiwari", "Security", "Guard", 650),
]


def _sundays():
    return {d for d in range(1, DAYS + 1) if date(YEAR, MONTH, d).weekday() == 6}


def _status(rng: random.Random, day: int, reliability: float) -> str:
    if day in HOLIDAYS:
        return "H"
    if day in _sundays():
        return "WO"
    r = rng.random()
    if r < reliability:
        return "P"
    if r < reliability + 0.04:
        return "HD"
    if r < reliability + 0.07:
        return "L"
    return "A"


def _title(ws, text, ncols):
    ws.append([text])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Period: October {YEAR}"])
    ws.append([])


def build(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)
    files = []

    # ---- 1. employee master -------------------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Factory Staff"
    _title(ws, "ACME Manufacturing – Employee Master (Factory)", 8)
    ws.append(["Emp ID", "Employee Name", "Department", "Designation", "Daily Wage",
               "Allowance", "Deduction", "Bank A/C No"])
    for r in PRODUCTION:
        ws.append(list(r))
    ws.append(["E009", "Arjun Reddy", "Production", "Helper", -600, 0, 0, ""])  # negative wage
    ws.append(["E010", "Pooja Mehta", "Stores", "Helper", "six hundred", 0, 0, ""])  # text wage
    ws.append(["E011", None, "Production", "Helper", 600, 0, 0, ""])  # blank name
    ws.append([None, "No Id Person", "Production", "Helper", 600, 0, 0, ""])  # missing id

    ws2 = wb.create_sheet("Office Staff")
    _title(ws2, "ACME Manufacturing – Employee Master (Office)", 8)
    ws2.append(["Employee Code", "Name", "Dept", "Designation", "Monthly Salary",
                "Allowances", "Deductions", "Account Number"])
    for r in OFFICE:
        ws2.append(list(r))
    ws2.append(["E003", "Mohammed Irfan", "Production", "Supervisor", 30000, 0, 0, ""])  # conflict dup
    p = out / "employees_master.xlsx"
    wb.save(p)
    files.append(p)

    # ---- 2. long attendance register ---------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Oct"
    ws.append(["Employee ID", "Date", "Status", "OT Hours"])
    reliab = {"E001": .93, "E002": .85, "E003": .97, "E004": .80, "E005": .90,
              "E006": .95, "E007": .88, "E008": .70, "E011": .90}
    for emp, rel in reliab.items():
        for d in range(1, DAYS + 1):
            st = _status(rng, d, rel)
            ot = rng.choice([0, 0, 0, 0, 1, 2, 2.5, 3]) if st == "P" else 0
            ws.append([emp, date(YEAR, MONTH, d), st, ot or None])
    # deliberate problems
    ws.append(["E001", date(YEAR, MONTH, 5), "X", None])        # unknown status (dup date too)
    ws.append(["E002", "31/02/2026", "P", None])                 # invalid date
    ws.append(["E999", date(YEAR, MONTH, 3), "P", 2])            # unknown employee
    ws.append(["E005", date(YEAR, MONTH, 6), "P", 15])           # excessive OT (duplicate date)
    ws.append(["E006", date(YEAR, MONTH - 1, 30), "P", None])    # outside period
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        for c in row:
            c.number_format = "DD-MM-YYYY"
    p = out / "attendance_production_oct.xlsx"
    wb.save(p)
    files.append(p)

    # ---- 3. wide muster roll for office staff ------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Muster Roll"
    _title(ws, "Office Muster Roll", DAYS + 3)
    ws.append(["Emp Code", "Name"] + list(range(1, DAYS + 1)) + ["OT Hours"])
    office_rel = {"M101": .96, "M102": .9, "M103": .98, "M104": .82, "M105": .93}
    for emp, name, *_ in OFFICE:
        row = [emp, name] + [_status(rng, d, office_rel[emp]) for d in range(1, DAYS + 1)]
        row.append(rng.choice([0, 4, 6, 10]) or None)
        ws.append(row)
    ws.cell(row=ws.max_row, column=2 + 14).value = "late"  # unknown code for M105 on 14th
    p = out / "muster_roll_office_oct.xlsx"
    wb.save(p)
    files.append(p)

    # ---- 4. contract staff: muster roll that also carries the wage ---------
    wb = Workbook()
    ws = wb.active
    ws.title = "Contract Oct"
    ws.append(["ID", "Worker Name", "Department", "Designation", "Rate per Day"] +
              [date(YEAR, MONTH, d) for d in range(1, DAYS + 1)])
    for emp, name, dept, desig, wage in CONTRACT:
        ws.append([emp, name, dept, desig, wage] + [_status(rng, d, .86) for d in range(1, DAYS + 1)])
    for c in ws[1][5:]:
        c.number_format = "DD-MMM"
    p = out / "contract_staff_oct.xlsx"
    wb.save(p)
    files.append(p)
    return files


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "sample_data"
    for f in build(target):
        print("written", f)
