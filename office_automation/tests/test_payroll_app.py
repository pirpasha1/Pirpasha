"""Tests for the payroll & attendance application.

Run:  python -m pytest -q          (from the office_automation folder)
"""
from __future__ import annotations

import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from payroll_app.cli import main as cli_main  # noqa: E402
from payroll_app.config import Settings  # noqa: E402
from payroll_app.filters import filter_daily, filter_payroll  # noqa: E402
from payroll_app.importer import import_files, normalise_employee_id  # noqa: E402
from payroll_app.numwords import amount_in_words  # noqa: E402
from payroll_app.payroll import compute_payroll  # noqa: E402
from payroll_app.reports_excel import build_consolidated_workbook  # noqa: E402
from payroll_app.reports_pdf import (all_statements_pdf, attendance_report_pdf,  # noqa: E402
                                     salary_statement_pdf, statements_zip)
import generate_sample_data  # noqa: E402

OCT = dict(year=2026, month=10)  # 31 days, 1 Oct 2026 is a Thursday


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def xlsx(rows: list[list], sheets: dict[str, list[list]] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    for name, data in (sheets or {}).items():
        sh = wb.create_sheet(name)
        for r in data:
            sh.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def run(files: dict[str, bytes], **kw):
    s = Settings(**{**OCT, **kw})
    data = import_files(list(files.items()), s)
    return data, compute_payroll(data, s)


def messages(data, severity=None):
    return [i.message for i in data.issues.issues if severity is None or i.severity == severity]


EMP = [["Employee ID", "Name", "Department", "Designation", "Daily Wage", "Allowance", "Deduction"],
       ["E1", "Asha", "Prod", "Operator", 800, 500, 200],
       ["E2", "Bala", "Stores", "Helper", 600, 0, 0]]


def att_rows(emp_id, statuses: dict[int, str], ot: dict[int, float] | None = None):
    ot = ot or {}
    return [[emp_id, date(2026, 10, d), st, ot.get(d)] for d, st in statuses.items()]


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    folder = tmp_path_factory.mktemp("sample")
    files = generate_sample_data.build(folder)
    s = Settings(company_name="ACME Test", **OCT)
    data = import_files(files, s)
    return data, compute_payroll(data, s)


# --------------------------------------------------------------------------
# configuration & helpers
# --------------------------------------------------------------------------
class TestSettings:
    def test_invalid_month(self):
        with pytest.raises(ValueError):
            Settings(year=2026, month=13)

    def test_invalid_divisor(self):
        with pytest.raises(ValueError):
            Settings(monthly_divisor="abc")
        with pytest.raises(ValueError):
            Settings(monthly_divisor=40)

    def test_period(self):
        s = Settings(year=2024, month=2)
        assert s.days_in_month == 29 and s.period_label == "February 2024"

    @pytest.mark.parametrize("raw,code", [("p", "P"), ("Present", "P"), (1, "P"), (1.0, "P"),
                                          ("absent", "A"), ("CL", "L"), ("half day", "HD"),
                                          ("Sunday", "WO"), ("lop", "LWP"), ("x", None), ("", None),
                                          (float("nan"), None)])
    def test_status_normalisation(self, raw, code):
        assert Settings().normalise_status(raw) == code

    def test_employee_id_normalisation(self):
        assert normalise_employee_id(101.0) == "101"
        assert normalise_employee_id(" e01 ") == "E01"
        assert normalise_employee_id(float("nan")) == ""


def test_amount_in_words():
    assert amount_in_words(22900) == "Rupees Twenty Two Thousand Nine Hundred Only"
    assert amount_in_words(1234567.5) == ("Rupees Twelve Lakh Thirty Four Thousand Five Hundred "
                                          "Sixty Seven and Fifty Paise Only")
    assert amount_in_words(0) == "Rupees Zero Only"
    assert amount_in_words(15.25, "USD") == "USD Fifteen and Twenty Five Cents Only"


# --------------------------------------------------------------------------
# import & validation
# --------------------------------------------------------------------------
class TestImport:
    def test_multiple_files_and_sheets_merge(self):
        att = [["Emp ID", "Date", "Status"]] + att_rows("E1", {1: "P", 2: "A"})
        att2 = [["Emp ID", "Date", "Status"]] + att_rows("E2", {1: "P"})
        data, _ = run({"emp.xlsx": xlsx(EMP), "a1.xlsx": xlsx(att), "a2.xlsx": xlsx([["x"]], {"Oct": att2})})
        assert list(data.employees.employee_id) == ["E1", "E2"]
        assert len(data.attendance) == 3
        assert set(data.files.file) == {"emp.xlsx", "a1.xlsx", "a2.xlsx"}

    def test_title_rows_and_column_aliases(self):
        rows = [["ACME Ltd"], ["Employee list"], [],
                ["EMP CODE", "Employee Name", "Dept.", "Rate Per Day"], ["7", "ravi kumar", "Yard", "₹ 1,200"]]
        data, _ = run({"e.xlsx": xlsx(rows)})
        e = data.employees.iloc[0]
        assert (e.employee_id, e["name"], e.department, e.daily_wage) == ("7", "Ravi Kumar", "Yard", 1200.0)
        assert "e.xlsx / Sheet (row 5)" in e.source  # real Excel row number reported

    def test_monthly_salary_employee(self):
        rows = [["ID", "Name", "Monthly Salary"], ["M1", "Sam", 31000]]
        att = [["ID", "Date", "Status"]] + att_rows("M1", {d: "P" for d in range(1, 32)})
        _, res = run({"e.xlsx": xlsx(rows), "a.xlsx": xlsx(att)})
        p = res.payroll.iloc[0]
        assert p.daily_wage == 1000 and p.gross_pay == 31000

    def test_monthly_salary_full_month_is_exact(self):
        rows = [["ID", "Name", "Monthly Salary"], ["M1", "Sam", 45000]]
        att = [["ID", "Date", "Status"]] + att_rows("M1", {d: "P" for d in range(1, 32)})
        _, res = run({"e.xlsx": xlsx(rows), "a.xlsx": xlsx(att)})
        assert res.payroll.iloc[0].basic_earnings == 45000.00  # not 44,999.91
        assert round(res.daily.day_earning.sum(), 2) == 45000.00

    def test_wide_muster_roll_with_wage(self):
        header = ["ID", "Name", "Daily Wage"] + list(range(1, 32)) + ["OT Hours"]
        row = ["W1", "Kiran", 500] + ["P"] * 31 + [4]
        data, res = run({"m.xlsx": xlsx([header, row])})
        assert len(data.employees) == 1 and len(data.attendance) == 31
        p = res.payroll.iloc[0]
        assert p.basic_earnings == 15500 and p.ot_hours == 4 and p.ot_pay == 4 * 500 / 8 * 2

    def test_wide_muster_roll_with_date_headers(self):
        header = ["Emp ID"] + [date(2026, 10, d) for d in range(1, 32)]
        data, _ = run({"e.xlsx": xlsx(EMP), "m.xlsx": xlsx([header, ["E2"] + ["A"] * 31])})
        assert len(data.attendance) == 31 and set(data.attendance.status) == {"A"}

    def test_not_excel_and_corrupt_file(self):
        data, _ = run({"notes.txt": b"hello", "bad.xlsx": b"not really a workbook", "e.xlsx": xlsx(EMP)})
        errs = messages(data, "ERROR")
        assert any("Not an Excel file" in m for m in errs)
        assert sum("Could not read file" in m for m in errs) == 2
        assert len(data.employees) == 2  # good file still processed

    def test_no_files(self):
        data = import_files([], Settings(**OCT))
        assert data.issues.has_errors and data.employees.empty

    def test_unrecognised_sheet(self):
        data, _ = run({"e.xlsx": xlsx(EMP, {"Notes": [["Remarks"], ["hello"]]})})
        assert any("No 'Employee ID' column" in m for m in messages(data, "WARNING"))

    def test_missing_wage_column(self):
        data, _ = run({"e.xlsx": xlsx([["ID", "Name"], ["E1", "A"]])})
        assert any("no 'Daily Wage' or 'Monthly Salary'" in m for m in messages(data))
        assert any("No valid employee records" in m for m in messages(data, "ERROR"))

    def test_invalid_employee_rows(self):
        rows = [["ID", "Name", "Daily Wage", "Allowance"],
                ["E1", "Ok", 500, -5],          # negative allowance -> warning, 0
                ["E2", "Neg", -100, 0],          # negative wage -> error, skipped
                ["E3", "Txt", "abc", 0],         # text wage -> error, skipped
                [None, "NoId", 500, 0],          # missing id -> error
                ["E4", None, 500, 0]]            # missing name -> warning, kept
        data, _ = run({"e.xlsx": xlsx(rows)})
        assert list(data.employees.employee_id) == ["E1", "E4"]
        assert data.employees.set_index("employee_id").at["E1", "allowance"] == 0
        errs = data.issues.to_frame()
        assert set(errs[errs.severity == "ERROR"].row.dropna()) == {3, 4, 5}
        assert any("name is blank" in m for m in messages(data, "WARNING"))

    def test_conflicting_duplicate_employee(self):
        dup = [["ID", "Name", "Daily Wage"], ["E1", "Asha", 999]]
        data, _ = run({"a.xlsx": xlsx(EMP), "b.xlsx": xlsx(dup)})
        assert data.employees.set_index("employee_id").at["E1", "daily_wage"] == 800  # first kept
        assert any("Conflicting duplicate" in m for m in messages(data, "WARNING"))

    def test_identical_duplicate_is_info_only(self):
        data, _ = run({"a.xlsx": xlsx(EMP), "b.xlsx": xlsx(EMP)})
        assert len(data.employees) == 2
        assert not any("duplicate" in m.lower() for m in messages(data, "WARNING"))

    def test_attendance_validation(self):
        att = [["Emp ID", "Date", "Status", "OT Hours"],
               ["E1", date(2026, 10, 1), "P", 2],
               ["E1", date(2026, 10, 2), "Z", None],          # unknown status
               ["E1", "not a date", "P", None],               # bad date
               ["E1", date(2026, 10, 3), None, None],         # blank status
               ["E1", date(2026, 10, 4), "P", "two"],         # bad OT
               ["E1", date(2026, 10, 5), "P", 20],            # excessive OT (kept)
               ["E1", date(2026, 10, 6), "A", 3],             # OT on absent day -> dropped
               ["E1", date(2026, 9, 30), "P", None],          # outside period
               ["E9", date(2026, 10, 1), "P", None],          # unknown employee
               ["E1", date(2026, 10, 1), "HD", None]]         # duplicate date, later wins
        data, res = run({"e.xlsx": xlsx(EMP), "a.xlsx": xlsx(att)})
        msgs = " | ".join(messages(data))
        for text in ("Unknown attendance status 'Z'", "Invalid or missing date", "Blank attendance status",
                     "'two' is not a number", "exceeds the limit", "non-working day",
                     "outside October 2026", "not in any employee list", "Duplicate attendance"):
            assert text in msgs, text
        a = data.attendance.set_index("date")
        assert a.at[date(2026, 10, 1), "status"] == "HD"
        assert a.at[date(2026, 10, 5), "ot_hours"] == 20
        assert a.at[date(2026, 10, 6), "ot_hours"] == 0
        assert "E9" not in set(data.attendance.employee_id)
        assert len(data.attendance) == 4  # 1, 4, 5, 6

    def test_unrecorded_days_warning(self):
        att = [["Emp ID", "Date", "Status"]] + att_rows("E1", {1: "P"})
        data, _ = run({"e.xlsx": xlsx(EMP), "a.xlsx": xlsx(att)})
        w = messages(data, "WARNING")
        assert any("1 of 31 days" in m for m in w)
        assert any("No attendance found" in m for m in w)  # E2


# --------------------------------------------------------------------------
# calculations
# --------------------------------------------------------------------------
class TestCalculations:
    @pytest.fixture
    def res(self):
        statuses = {1: "P", 2: "H", 3: "P", 4: "WO", 5: "HD", 6: "A", 7: "L", 8: "LWP"}
        att = [["Emp ID", "Date", "Status", "OT Hours"]] + att_rows("E1", statuses, {1: 2, 3: 1.5})
        return run({"e.xlsx": xlsx(EMP), "a.xlsx": xlsx(att)})[1]

    def test_daily_wages(self, res):
        d = res.daily.set_index("date")
        assert d.at[date(2026, 10, 1), "day_earning"] == 800
        assert d.at[date(2026, 10, 1), "ot_pay"] == 400       # 2 h x 800/8 x 2
        assert d.at[date(2026, 10, 1), "total_earning"] == 1200
        assert d.at[date(2026, 10, 3), "ot_pay"] == 300       # 1.5 h x 100 x 2
        assert d.at[date(2026, 10, 5), "day_earning"] == 400  # half day
        assert d.at[date(2026, 10, 6), "day_earning"] == 0    # absent
        assert d.at[date(2026, 10, 8), "day_earning"] == 0    # LWP
        assert d.at[date(2026, 10, 1), "weekday"] == "Thu"

    def test_monthly_payment(self, res):
        p = res.payroll.set_index("employee_id").loc["E1"]
        # paid: P,H,P,WO,HD(.5),L = 5.5 days ; worked: P,P,HD = 2.5
        assert p.paid_days == 5.5 and p.worked_days == 2.5
        assert p.basic_earnings == 4400
        assert p.ot_hours == 3.5 and p.ot_pay == 700
        assert p.gross_pay == 4400 + 700 + 500
        assert p.net_pay == 5600 - 200
        # scheduled = 8 recorded - 1 holiday - 1 weekly off = 6 ; 2.5/6
        assert p.attendance_pct == round(2.5 / 6 * 100, 1)
        assert p.unrecorded_days == 23
        assert (p.present, p.half_days, p.absent, p.paid_leave, p.leave_without_pay) == (2, 1, 1, 1, 1)

    def test_employee_without_attendance_gets_nothing(self, res):
        p = res.payroll.set_index("employee_id").loc["E2"]
        assert p.gross_pay == 0 and p.allowance == 0 and p.net_pay == 0

    def test_custom_settings(self):
        att = [["Emp ID", "Date", "Status", "OT Hours"]] + att_rows("E1", {1: "P"}, {1: 2})
        _, res = run({"e.xlsx": xlsx(EMP), "a.xlsx": xlsx(att)}, standard_hours=10, overtime_multiplier=1.5)
        assert res.payroll.set_index("employee_id").at["E1", "ot_pay"] == 2 * 80 * 1.5

    def test_fixed_divisor(self):
        rows = [["ID", "Name", "Monthly Salary"], ["M1", "Sam", 26000]]
        att = [["ID", "Date", "Status"]] + att_rows("M1", {1: "P", 2: "P"})
        _, res = run({"e.xlsx": xlsx(rows), "a.xlsx": xlsx(att)}, monthly_divisor=26)
        assert res.payroll.iloc[0].daily_wage == 1000 and res.payroll.iloc[0].basic_earnings == 2000

    def test_negative_net_pay_warning(self):
        rows = [["ID", "Name", "Daily Wage", "Deduction"], ["E1", "A", 100, 5000]]
        att = [["ID", "Date", "Status"]] + att_rows("E1", {1: "P"})
        _, res = run({"e.xlsx": xlsx(rows), "a.xlsx": xlsx(att)})
        assert res.payroll.iloc[0].net_pay == -4900
        assert any("net pay is negative" in i.message for i in res.issues.issues)

    def test_attendance_matrix_and_department_summary(self, res):
        m = res.attendance_matrix.set_index("employee_id")
        assert m.at["E1", 1] == "P" and m.at["E1", 2] == "H" and m.at["E1", 31] == ""
        dsum = res.department_summary.set_index("department")
        assert dsum.at["Prod", "net_pay"] == 5400 and dsum.at["Stores", "employees"] == 1


# --------------------------------------------------------------------------
# search & filter
# --------------------------------------------------------------------------
class TestFilters:
    def test_search_and_filters(self, sample):
        _, res = sample
        p = res.payroll
        assert set(filter_payroll(p, "ravi").employee_id) == {"E001"}
        assert set(filter_payroll(p, "qc inspector").employee_id) == {"E006", "E007"}  # AND of words
        assert set(filter_payroll(p, "m10").employee_id) == {f"M10{i}" for i in range(1, 6)}
        assert set(filter_payroll(p, departments=["Accounts"]).employee_id) == {"M101", "M102"}
        assert set(filter_payroll(p, designations=["Loader"]).employee_id) == {"C201", "C202"}
        low = filter_payroll(p, max_attendance=80)
        assert len(low) and (low.attendance_pct <= 80).all()
        rich = filter_payroll(p, min_net=40000)
        assert len(rich) and (rich.net_pay >= 40000).all()
        assert filter_payroll(p, "no such person").empty

    def test_daily_filter(self, sample):
        _, res = sample
        d = filter_daily(res.daily, employee_ids=["E001"], statuses=["P"],
                         start=date(2026, 10, 1), end=date(2026, 10, 10))
        assert len(d) and set(d.status) == {"P"} and d.date.max() <= date(2026, 10, 10)


# --------------------------------------------------------------------------
# sample data end-to-end
# --------------------------------------------------------------------------
class TestSampleData:
    def test_sample_import(self, sample):
        data, res = sample
        assert len(data.files) == 5
        assert len(res.payroll) == 18
        # the deliberate data errors in the sample files are all detected
        msgs = " | ".join(messages(data))
        for text in ("found -600", "'six hundred' is not a number", "Missing employee ID",
                     "Unknown attendance status 'X'", "Unknown attendance status 'late'", "'31/02/2026'",
                     "Conflicting duplicate", "exceeds the limit", "not in any employee list"):
            assert text in msgs, text

    def test_hand_checked_employee(self, sample):
        _, res = sample
        p = res.payroll.set_index("employee_id")
        e = p.loc["E002"]  # 600/day, allowance 300, deduction 200
        assert e.basic_earnings == round(e.paid_days * 600, 2)
        assert e.ot_pay == round(e.ot_hours * 600 / 8 * 2, 2)
        assert e.net_pay == round(e.basic_earnings + e.ot_pay + 300 - 200, 2)
        assert p.loc["M103"].basic_earnings == 45000  # full month of a 45,000 salary

    def test_totals_consistent(self, sample):
        _, res = sample
        p = res.payroll
        assert (abs(p.gross_pay - (p.basic_earnings + p.ot_pay + p.allowance)) < 0.011).all()
        assert (abs(p.net_pay - (p.gross_pay - p.deduction)) < 0.011).all()
        for emp_id, g in res.daily.groupby("employee_id"):
            assert abs(g.day_earning.sum() - p.set_index("employee_id").at[emp_id, "basic_earnings"]) < 0.001
        assert (p.paid_days <= p.days_in_month).all()


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------
class TestReports:
    def test_consolidated_excel(self, sample):
        data, res = sample
        wb = load_workbook(io.BytesIO(build_consolidated_workbook(res, data.issues)))
        assert wb.sheetnames == ["Summary", "Salary Register", "Attendance Summary", "Attendance Register",
                                 "Daily Wages", "Employees", "Validation Issues"]
        reg = pd.read_excel(io.BytesIO(build_consolidated_workbook(res, data.issues)),
                            sheet_name="Salary Register", header=3)
        body = reg[reg["Employee ID"] != "TOTAL"]
        assert len(body) == 18
        total = reg[reg["Employee ID"] == "TOTAL"].iloc[0]
        assert round(total["Net Pay"], 2) == round(res.payroll.net_pay.sum(), 2)
        val = pd.read_excel(io.BytesIO(build_consolidated_workbook(res, data.issues)),
                            sheet_name="Validation Issues", header=3)
        assert (val["Severity"] == "ERROR").sum() == data.issues.count("ERROR")

    def test_excel_filtered_subset(self, sample):
        data, res = sample
        sub = filter_payroll(res.payroll, departments=["Accounts"])
        raw = build_consolidated_workbook(res, data.issues, sub)
        daily = pd.read_excel(io.BytesIO(raw), sheet_name="Daily Wages", header=3)
        assert set(daily["Employee ID"].dropna()) - {"TOTAL"} == {"M101", "M102"}

    def test_salary_statement_pdf(self, sample):
        _, res = sample
        reader = PdfReader(io.BytesIO(salary_statement_pdf(res, "E002")))
        assert len(reader.pages) == 1
        text = reader.pages[0].extract_text()
        net = res.payroll.set_index("employee_id").at["E002", "net_pay"]
        for t in ("Sunita Devi", "E002", "October 2026", f"{net:,.2f}", "Daily Wage Details", "ACME Test"):
            assert t in text, t

    def test_all_statements_fit_one_page(self, sample):
        _, res = sample
        for emp_id in res.payroll.employee_id:
            assert len(PdfReader(io.BytesIO(salary_statement_pdf(res, emp_id))).pages) == 1, emp_id

    def test_unknown_employee_statement(self, sample):
        _, res = sample
        with pytest.raises(KeyError):
            salary_statement_pdf(res, "NOPE")

    def test_zip_and_combined_pdf(self, sample):
        _, res = sample
        zf = zipfile.ZipFile(io.BytesIO(statements_zip(res, ["E001", "M101"])))
        assert sorted(zf.namelist()) == ["Salary_E001_Ravi_Kumar_2026-10.pdf", "Salary_M101_Deepa_Iyer_2026-10.pdf"]
        assert zf.read(zf.namelist()[0]).startswith(b"%PDF")
        assert len(PdfReader(io.BytesIO(all_statements_pdf(res))).pages) == 18

    def test_attendance_pdf(self, sample):
        _, res = sample
        reader = PdfReader(io.BytesIO(attendance_report_pdf(res)))
        text = " ".join(p.extract_text() for p in reader.pages)
        assert "Attendance Report" in text and "Day-wise Attendance Register" in text and "Kavita Rao" in text

    def test_reports_with_no_attendance(self):
        _, res = run({"e.xlsx": xlsx(EMP)})
        assert salary_statement_pdf(res, "E1").startswith(b"%PDF")
        assert attendance_report_pdf(res).startswith(b"%PDF")
        load_workbook(io.BytesIO(build_consolidated_workbook(res)))


# --------------------------------------------------------------------------
# command line & user interface
# --------------------------------------------------------------------------
def test_cli(tmp_path, capsys):
    files = generate_sample_data.build(tmp_path / "in")
    code = cli_main([*map(str, files), "--month", "2026-10", "--out", str(tmp_path / "out")])
    assert code == 0
    out = tmp_path / "out"
    assert (out / "Payroll_Report_2026-10.xlsx").exists()
    assert (out / "Attendance_Report_2026-10.pdf").exists()
    assert len(list((out / "Salary_Statements_2026-10").glob("*.pdf"))) == 18
    assert "Employees: 18" in capsys.readouterr().out


def test_cli_no_valid_data(tmp_path):
    bad = tmp_path / "x.xlsx"
    bad.write_bytes(xlsx([["hello"]]))
    assert cli_main([str(bad), "--month", "2026-10", "--out", str(tmp_path / "o")]) == 1


def test_streamlit_ui():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception
    at.button[0].click().run()  # "Load sample data"
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Employees"] == "18" and metrics["Errors"] == "8"
    at.sidebar.text_input(key="search").input("accounts").run()
    assert not at.exception
    assert any("Showing **2** of 18" in c.value for c in at.sidebar.caption)
    next(b for b in at.button if b.label.startswith("⚙️ Prepare Excel")).click().run()
    assert not at.exception
    assert not any(b.label.startswith("⚙️ Prepare Excel") for b in at.button)  # replaced by download
