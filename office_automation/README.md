# Payroll & Attendance Automation

An office automation application that turns a pile of Excel sheets into a
finished payroll: it imports employee lists and attendance from **multiple
Excel files**, checks the data, calculates **daily wages and monthly pay**, and
produces **salary statements (PDF)**, an **attendance report** and a
**consolidated Excel report** — with search and filters throughout.

## Quick start

```bash
cd office_automation
pip install -r requirements.txt
streamlit run app.py            # opens http://localhost:8501 in your browser
```

On Windows you can simply double-click **`run_app.bat`** (macOS/Linux: `./run_app.sh`).

In the app, click **Load sample data (Oct 2026)** to try it immediately, or
upload your own files.

## Features

| Requirement | Where |
|---|---|
| Import multiple Excel files | Upload any number of `.xlsx/.xlsm/.xls` files; **every sheet** is read and auto-classified |
| Extract & organise employee records | *Employees* tab – merged, de-duplicated, sorted, with the source file/sheet/row of each record |
| Daily wages & monthly payments | *Attendance* tab (daily records) and *Payroll* tab (salary register, department totals) |
| Employee-wise salary statements | *Salary Statements* tab – on-screen statement + one-page PDF per employee |
| Attendance reports | *Attendance* tab (summary, colour-coded day-wise register) + landscape PDF report |
| Individual PDF reports | *Export* tab – ZIP with one PDF per employee, or a single combined PDF for printing |
| Consolidated Excel report | *Export* tab – formatted workbook with 7 sheets (see below) |
| Search & filtering | Sidebar: free-text search (name / ID / department / designation), department, designation, attendance % range, net-pay range – applies to every tab and to exports |
| Error checking & validation | *Import & Validation* tab – every problem listed with **file, sheet, Excel row and employee** |

### Accepted Excel layouts

Column names are matched automatically (case-insensitive; common variants such as
`Emp ID`, `Employee Code`, `Rate per Day`, `Dept.` are recognised). Title rows
above the header are skipped.

| Layout | Required columns | Optional |
|---|---|---|
| **Employee list** | `Employee ID`, `Name`, `Daily Wage` *or* `Monthly Salary` | `Department`, `Designation`, `Allowance`, `Deduction`, `Bank Account` |
| **Attendance register** (one row per day) | `Employee ID`, `Date`, `Status` | `OT Hours` |
| **Muster roll** (one row per employee) | `Employee ID` + day columns `1`…`31` or real dates | `OT Hours` (monthly total). Add a wage column and the sheet is also an employee list. |

**Status codes** (editable in *Attendance codes* in the sidebar):

| Code | Meaning | Paid | Counts as worked |
|---|---|---|---|
| P | Present | 1 | 1 |
| HD | Half day | 0.5 | 0.5 |
| A | Absent | 0 | 0 |
| L | Paid leave (also CL/SL/EL/PL) | 1 | 0 |
| LWP | Leave without pay (also LOP) | 0 | 0 |
| H | Holiday | 1 | 0 |
| WO | Weekly off (also "Sunday") | 1 | 0 |

### Calculation rules

* **Daily wage** = `Daily Wage` column, or `Monthly Salary ÷ days in the month`
  (or a fixed divisor such as 26 – set in *Settings*).
* **Day earning** = daily wage × paid fraction of the day's status.
* **Overtime pay** = OT hours × (daily wage ÷ standard hours) × OT multiplier
  (defaults: 8 hours, ×2).
* **Gross pay** = wages earned + overtime pay + allowance.
  **Net pay** = gross pay − deductions.
* **Attendance %** = days worked ÷ scheduled working days (recorded days excluding holidays and weekly offs).
* Amounts are rounded half-up to 2 decimals so that daily amounts always add
  up exactly to the monthly figure (a full month of a 45,000 salary is exactly 45,000.00).
* Days with no attendance record are **not paid** and are reported as warnings.

### Validation performed

* Unreadable / non-Excel files, empty or unrecognised sheets, missing required columns
* Missing employee ID or name, non-numeric / zero / negative wages, negative allowances or deductions
* Duplicate employee IDs across files (conflicting data is flagged; first record is used)
* Invalid dates, dates outside the selected month, blank or unknown status codes
* Duplicate attendance for the same employee and day (latest entry wins, change reported)
* Non-numeric, negative or excessive overtime; overtime on non-working days
* Attendance for employees who are not in any employee list; employees with missing days or no attendance
* Deductions larger than gross pay (negative net pay)

Errors skip only the affected row; everything else is still processed.

### Consolidated Excel report

`Summary` (totals, calculation rules, department summary) · `Salary Register` ·
`Attendance Summary` · `Attendance Register` (colour-coded day-wise grid) ·
`Daily Wages` · `Employees` · `Validation Issues` — with headers, number
formats, totals rows, frozen panes and auto-filters.

## Command-line / batch mode

```bash
python -m payroll_app.cli data/*.xlsx --month 2026-10 --company "ACME Ltd" --out reports
```

Writes the Excel report, the attendance PDF and one salary-statement PDF per
employee into `reports/`, and prints every validation issue. Options:
`--divisor 26`, `--hours 8`, `--ot-rate 2`, `--currency Rs.`, `--no-pdf`.

## Sample data & tests

`sample_data/` holds four demo files for October 2026 in different layouts
(18 valid employees, 557 attendance entries) with deliberate mistakes to show
the validation. Regenerate them with `python scripts/generate_sample_data.py`.

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 55 tests: import, validation, calculations, filters, PDF, Excel, CLI, UI
```

## Project layout

```
office_automation/
├── app.py                    Streamlit user interface
├── payroll_app/
│   ├── config.py             settings, status codes
│   ├── importer.py           multi-file Excel import + validation
│   ├── validation.py         error / warning log
│   ├── payroll.py            daily wage & monthly pay calculations
│   ├── filters.py            search & filter helpers
│   ├── reports_excel.py      consolidated Excel workbook
│   ├── reports_pdf.py        salary statements & attendance PDF
│   ├── numwords.py           amount in words (lakh / crore)
│   └── cli.py                command-line batch mode
├── scripts/generate_sample_data.py
├── sample_data/              demo Excel files
└── tests/test_payroll_app.py
```
