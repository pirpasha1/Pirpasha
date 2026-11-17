"""Office Automation – Payroll & Attendance (Streamlit user interface).

Run with:   streamlit run app.py
"""
from __future__ import annotations

import calendar
import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from payroll_app.config import DEFAULT_STATUS_CODES, Settings, StatusCode
from payroll_app.filters import filter_daily, filter_payroll, search_mask
from payroll_app.importer import import_files
from payroll_app.payroll import compute_payroll
from payroll_app.reports_excel import DECIMAL, HEADERS, MONEY, PERCENT, build_consolidated_workbook
from payroll_app.reports_pdf import (all_statements_pdf, attendance_report_pdf, safe_filename,
                                     salary_statement_pdf, statement_filename, statements_zip)

APP_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = APP_DIR / "sample_data"
STATUS_BG = {"P": "#C6EFCE", "A": "#FFC7CE", "HD": "#FFEB9C", "L": "#BDD7EE", "LWP": "#F8CBAD",
             "H": "#D9D9D9", "WO": "#EDEDED"}

st.set_page_config(page_title="Payroll & Attendance", page_icon="🧾", layout="wide")


# --------------------------------------------------------------------------
# cached processing
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Reading Excel files and calculating wages…")
def process(files: tuple[tuple[str, bytes], ...], settings_key: tuple, codes: tuple):
    company, year, month, currency, divisor, std_hours, ot_mult, max_ot = settings_key
    s = Settings(company_name=company, year=year, month=month, currency=currency,
                 monthly_divisor=divisor, standard_hours=std_hours, overtime_multiplier=ot_mult,
                 max_overtime_hours=max_ot,
                 status_codes={c[0]: StatusCode(*c) for c in codes})
    data = import_files(list(files), s)
    result = compute_payroll(data, s)
    return data, result


def money(x: float, cur: str) -> str:
    return f"{cur} {x:,.2f}"


def amount(x: float) -> str:
    """Short number for metric tiles (currency goes in the label)."""
    return f"{x:,.0f}"


def col_cfg(df: pd.DataFrame, **overrides) -> dict:
    """Friendly column titles and number formats for st.dataframe."""
    cfg = {}
    for c in df.columns:
        label = HEADERS.get(str(c), str(c))
        if c in MONEY:
            cfg[c] = st.column_config.NumberColumn(label, format="%.2f")
        elif c in PERCENT:
            cfg[c] = st.column_config.NumberColumn(label, format="%.1f%%")
        elif c in DECIMAL:
            cfg[c] = st.column_config.NumberColumn(label, format="%g")
        elif c == "date":
            cfg[c] = st.column_config.DateColumn(label, format="DD-MMM-YYYY")
        else:
            cfg[c] = label
    cfg.update(overrides)
    return cfg


def fingerprint(*parts) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(repr(p).encode())
    return h.hexdigest()[:16]


def lazy_download(label: str, key: str, fp: str, builder, file_name: str, mime: str, help: str = ""):
    """Two-step download: build on click (can take a few seconds), then download."""
    store = st.session_state.setdefault("downloads", {})
    entry = store.get(key)
    if entry is None or entry[0] != fp:
        if st.button(f"⚙️ Prepare {label}", key=f"prep_{key}", help=help, width="stretch"):
            with st.spinner(f"Creating {label}…"):
                try:
                    store[key] = (fp, builder())
                except Exception as exc:  # show, never crash the UI
                    st.error(f"Could not create {label}: {exc}")
                    return
            st.rerun()
    else:
        st.download_button(f"⬇️ Download {label}", data=entry[1], file_name=file_name, mime=mime,
                           key=f"dl_{key}", type="primary", width="stretch")


# --------------------------------------------------------------------------
# sidebar – settings & filters
# --------------------------------------------------------------------------
# defaults (set once; widgets below read them through their keys)
_today = date.today()
for _k, _v in {"company": "My Company Pvt. Ltd.", "month": _today.month, "year": _today.year,
               "currency": "Rs."}.items():
    st.session_state.setdefault(_k, _v)



def _load_sample() -> None:
    st.session_state.update(use_sample=True, month=10, year=2026, company="ACME Manufacturing Pvt. Ltd.")


def _clear_sample() -> None:
    st.session_state["use_sample"] = False


st.sidebar.title("🧾 Payroll & Attendance")
with st.sidebar.expander("⚙️ Settings", expanded=False):
    company = st.text_input("Company name", key="company")
    c1, c2 = st.columns(2)
    month = c1.selectbox("Month", list(range(1, 13)), format_func=lambda m: calendar.month_name[m],
                         key="month")
    year = c2.number_input("Year", min_value=2000, max_value=2100, step=1, key="year")
    currency = st.text_input("Currency label", key="currency")
    div_choice = st.radio("Monthly salary → daily wage", ["Days in the month", "Fixed number of days"],
                          help="Used only for employees who have a Monthly Salary instead of a Daily Wage.",
                          key="div_choice")
    divisor = "calendar"
    if div_choice == "Fixed number of days":
        divisor = st.number_input("Days", min_value=1, max_value=31, value=26, key="div_days")
        st.caption("Tip: with a fixed 26-day divisor set the *Paid* value of WO (weekly off) to 0 below.")
    std_hours = st.number_input("Standard hours per day", 1.0, 24.0, 8.0, 0.5, key="std_hours")
    ot_mult = st.number_input("Overtime rate (× hourly wage)", 0.0, 5.0, 2.0, 0.25, key="ot_mult")
    max_ot = st.number_input("Flag OT above (hours/day)", 1.0, 24.0, 12.0, 0.5, key="max_ot")

with st.sidebar.expander("🏷️ Attendance codes", expanded=False):
    st.caption("Edit how much of a day each code *pays* and counts as *worked* (0 – 1).")
    codes_df = pd.DataFrame([vars(c) for c in DEFAULT_STATUS_CODES.values()])
    edited = st.data_editor(codes_df, hide_index=True, disabled=["code"], key="codes_editor",
                            column_config={
                                "worked": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.5),
                                "paid": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.5)})
    codes = tuple((r.code, str(r.label), float(r.worked), float(r.paid)) for r in edited.itertuples())

# --------------------------------------------------------------------------
# main – file import
# --------------------------------------------------------------------------
st.title("Payroll & Attendance Automation")
st.caption("Import employee lists and attendance sheets from multiple Excel files → validate → "
           "calculate daily wages and monthly pay → generate salary statements and reports.")

up_col, sample_col = st.columns([3, 1])
uploads = up_col.file_uploader(
    "**Step 1 – Select one or more Excel files** (employee lists, attendance registers, muster rolls)",
    type=["xlsx", "xlsm", "xls"], accept_multiple_files=True, key="uploads")
with sample_col:
    st.write("")
    st.write("")
    st.button("📂 Load sample data (Oct 2026)", width="stretch", on_click=_load_sample,
              help="Loads the demo files from the sample_data folder")
    if st.session_state.get("use_sample"):
        st.button("✖ Clear sample data", width="stretch", on_click=_clear_sample)

files: list[tuple[str, bytes]] = [(u.name, u.getvalue()) for u in uploads or []]
if st.session_state.get("use_sample"):
    files += [(p.name, p.read_bytes()) for p in sorted(SAMPLE_DIR.glob("*.xlsx"))]

with st.expander("ℹ️ What should my Excel files look like?", expanded=not files):
    st.markdown("""
Column names are matched automatically (case-insensitive, common variations accepted). A title block above the
header row is fine. Every sheet of every file is read.

| File type | Required columns | Optional columns |
|---|---|---|
| **Employee list** | `Employee ID`, `Name`, and `Daily Wage` **or** `Monthly Salary` | `Department`, `Designation`, `Allowance`, `Deduction`, `Bank Account` |
| **Attendance register** (one row per day) | `Employee ID`, `Date`, `Status` | `OT Hours` |
| **Muster roll** (one row per employee) | `Employee ID` + one column per day (`1`…`31` or dates) | `OT Hours` (monthly total); a wage column makes it an employee list too |

**Status codes:** P = Present, A = Absent, HD = Half day, L = Paid leave, LWP = Leave without pay,
H = Holiday, WO = Weekly off (words such as *Present*, *Absent*, *CL*, *Sunday* are also understood).
""")

if not files:
    st.info("👆 Upload your Excel files or click **Load sample data** to try the application.")
    st.stop()

try:
    settings_key = (company.strip() or "Company", int(year), int(month), currency.strip() or "Rs.",
                    divisor if divisor == "calendar" else int(divisor), float(std_hours), float(ot_mult),
                    float(max_ot))
    Settings(company_name=settings_key[0], year=settings_key[1], month=settings_key[2])  # validate
    data, result = process(tuple(files), settings_key, codes)
except ValueError as exc:
    st.error(f"Settings problem: {exc}")
    st.stop()

s = result.settings
cur = s.currency
issues = data.issues.to_frame()
n_err, n_warn = data.issues.count("ERROR"), data.issues.count("WARNING") + result.issues.count("WARNING")

if data.employees.empty:
    st.error("No valid employee records were found in the selected files. "
             "Open **Import & Validation** below to see what went wrong.")

# ---- sidebar filters ------------------------------------------------------
pay_all = result.payroll
st.sidebar.markdown("### 🔎 Search & filter")
search = st.sidebar.text_input("Search name / ID / department", key="search",
                               placeholder="e.g. ravi  or  E00  or  stores")
depts = st.sidebar.multiselect("Department", sorted(pay_all["department"].unique()), key="f_dept")
desigs = st.sidebar.multiselect("Designation", sorted(d for d in pay_all["designation"].unique() if d),
                                key="f_desig")
att_range = st.sidebar.slider("Attendance %", 0, 100, (0, 100), key="f_att")
if len(pay_all):
    lo, hi = float(pay_all["net_pay"].min()), float(pay_all["net_pay"].max())
    lo, hi = (min(lo, 0.0), max(hi, 1.0))
    net_range = st.sidebar.slider(f"Net pay ({cur})", lo, hi, (lo, hi), key="f_net")
else:
    net_range = (None, None)
pay = filter_payroll(pay_all, search, depts, desigs, att_range[0], att_range[1], *net_range)
ids = set(pay["employee_id"])
st.sidebar.caption(f"Showing **{len(pay)}** of {len(pay_all)} employees")

# ---- headline metrics -----------------------------------------------------
st.subheader(f"{s.company_name} — {s.period_label}")
m = st.columns(6)
m[0].metric("Files read", len({f for f, _ in files}))
m[1].metric("Employees", len(pay_all))
m[2].metric("Attendance entries", f"{len(data.attendance):,}")
m[3].metric(f"Total net pay ({cur})", amount(float(pay_all["net_pay"].sum())) if len(pay_all) else "-")
m[4].metric("Errors", n_err, help="Rows that were skipped – fix them in the Excel file")
m[5].metric("Warnings", n_warn, help="Data that was accepted but should be checked")
if n_err:
    st.warning(f"⚠️ {n_err} error(s) found – the affected rows were skipped. "
               "See the **Import & Validation** tab for file, sheet and row numbers.")

tabs = st.tabs(["📥 Import & Validation", "👥 Employees", "🗓️ Attendance", "💰 Payroll",
                "📄 Salary Statements", "📤 Export Reports"])

# ---- 1. import & validation -----------------------------------------------
with tabs[0]:
    st.markdown("#### Files and sheets processed")
    st.dataframe(data.files, hide_index=True, column_config={
        "file": "File", "sheet": "Sheet", "detected_as": "Detected as", "rows": "Data rows"})
    st.markdown("#### Validation results")
    all_issues = pd.concat([issues, result.issues.to_frame()], ignore_index=True)
    if all_issues.empty:
        st.success("✅ All data passed validation.")
    else:
        sev = st.multiselect("Show", ["ERROR", "WARNING", "INFO"], default=["ERROR", "WARNING"], key="sev")
        q = st.text_input("Search messages", key="issue_q", placeholder="e.g. E005 or 'duplicate'")
        view = all_issues[all_issues["severity"].isin(sev)]
        if q:
            view = view[search_mask(view, q, ("message", "file", "sheet", "employee_id"))]
        st.dataframe(view.style.map(
            lambda v: {"ERROR": "background-color:#FFC7CE", "WARNING": "background-color:#FFEB9C",
                       "INFO": "background-color:#DDEBF7"}.get(v, ""), subset=["severity"]),
            hide_index=True, column_config={
                "severity": "Severity", "message": st.column_config.TextColumn("Message", width="large"),
                "file": "File", "sheet": "Sheet", "row": "Excel row", "employee_id": "Employee"})

# ---- 2. employees ---------------------------------------------------------
with tabs[1]:
    emp = data.employees[data.employees["employee_id"].isin(ids)]
    st.markdown(f"#### Employee records ({len(emp)})")
    st.dataframe(emp, hide_index=True, column_config=col_cfg(emp))

# ---- 3. attendance --------------------------------------------------------
with tabs[2]:
    att = result.attendance_summary[result.attendance_summary["employee_id"].isin(ids)]
    a = st.columns(4)
    a[0].metric("Average attendance", f"{att['attendance_pct'].mean():.1f}%" if len(att) else "-")
    a[1].metric("Total absences", int(att["absent"].sum()) if len(att) else 0)
    a[2].metric("Below 75%", int((att["attendance_pct"] < 75).sum()) if len(att) else 0)
    a[3].metric("Total OT hours", f"{att['ot_hours'].sum():g}" if len(att) else 0)
    st.markdown("#### Attendance summary")
    st.dataframe(att, hide_index=True, column_config=col_cfg(att, attendance_pct=st.column_config.ProgressColumn(
        "Attendance %", min_value=0, max_value=100, format="%.1f%%")))
    st.markdown("#### Day-wise attendance register")
    mat = result.attendance_matrix[result.attendance_matrix["employee_id"].isin(ids)].copy()
    mat.columns = [str(c) for c in mat.columns]
    day_cols = [c for c in mat.columns if c.isdigit()]
    st.dataframe(mat.style.map(lambda v: f"background-color:{STATUS_BG[v]}" if v in STATUS_BG else "",
                               subset=day_cols), hide_index=True,
                 column_config={"employee_id": "ID", "name": "Name", "department": "Department",
                                **{d: st.column_config.TextColumn(d, width=36) for d in day_cols}})
    st.caption(" · ".join(f"**{c.code}** {c.label}" for c in s.status_codes.values()))

    st.markdown("#### Daily attendance & wage records")
    c1, c2, c3 = st.columns([2, 2, 2])
    sel_emp = c1.multiselect("Employee", sorted(ids), key="d_emp",
                             format_func=lambda i: f"{i} – {pay_all.set_index('employee_id').at[i, 'name']}")
    sel_status = c2.multiselect("Status", list(s.status_codes), key="d_status")
    dr = c3.date_input("Date range", (s.period_start, s.period_end), min_value=s.period_start,
                       max_value=s.period_end, key="d_range")
    start, end = (dr if isinstance(dr, tuple) and len(dr) == 2 else (s.period_start, s.period_end))
    daily = filter_daily(result.daily[result.daily["employee_id"].isin(ids)], "", sel_emp, sel_status,
                         start, end)
    st.dataframe(daily, hide_index=True, column_config=col_cfg(daily))
    st.caption(f"{len(daily)} record(s) · total earnings {money(float(daily['total_earning'].sum()), cur)}")

# ---- 4. payroll -----------------------------------------------------------
with tabs[3]:
    t = st.columns(5)
    t[0].metric("Employees", len(pay))
    t[1].metric(f"Gross pay ({cur})", amount(float(pay["gross_pay"].sum())))
    t[2].metric(f"Overtime pay ({cur})", amount(float(pay["ot_pay"].sum())))
    t[3].metric(f"Deductions ({cur})", amount(float(pay["deduction"].sum())))
    t[4].metric(f"Net pay ({cur})", amount(float(pay["net_pay"].sum())))
    st.markdown("#### Salary register")
    st.dataframe(pay, hide_index=True, column_config=col_cfg(pay))
    st.markdown("#### By department")
    from payroll_app.payroll import department_summary
    dsum = department_summary(pay)
    c1, c2 = st.columns([3, 2])
    c1.dataframe(dsum, hide_index=True, column_config=col_cfg(dsum))
    if len(dsum):
        c2.bar_chart(dsum.set_index("department")[["net_pay"]], horizontal=True, y_label="",
                     x_label=f"Net pay ({cur})")

# ---- 5. salary statements --------------------------------------------------
with tabs[4]:
    if pay.empty:
        st.info("No employees match the current filters.")
    else:
        names = pay.set_index("employee_id")["name"].to_dict()
        emp_id = st.selectbox("Select employee", list(pay["employee_id"]),
                              format_func=lambda i: f"{i} – {names[i]}", key="stmt_emp")
        r = pay.set_index("employee_id").loc[emp_id]
        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {r['name']}  \n{r.designation or ''} · {r.department} · ID {emp_id}")
            k = st.columns(4)
            k[0].metric("Paid days", f"{r.paid_days:g}")
            k[1].metric("Attendance", f"{r.attendance_pct:.1f}%")
            k[2].metric(f"Gross pay ({cur})", f"{r.gross_pay:,.2f}")
            k[3].metric(f"Net pay ({cur})", f"{r.net_pay:,.2f}")
            st.table(pd.DataFrame({
                "Item": [f"Wages earned ({r.paid_days:g} days × {money(r.daily_wage, cur)})",
                         f"Overtime ({r.ot_hours:g} h)", "Allowance", "Gross pay", "Deductions", "NET PAY"],
                "Amount": [money(v, cur) for v in (r.basic_earnings, r.ot_pay, r.allowance, r.gross_pay,
                                                   r.deduction, r.net_pay)]}).set_index("Item"))
        with right:
            st.markdown("#### Download")
            pdf = salary_statement_pdf(result, emp_id)
            st.download_button("⬇️ Salary statement (PDF)", data=pdf,
                               file_name=statement_filename(result, emp_id), mime="application/pdf",
                               type="primary", width="stretch", key=f"pdf_{emp_id}")
            st.caption(f"Wage basis: {r.wage_basis}")
        st.markdown("#### Daily breakdown")
        dd = result.daily[result.daily["employee_id"] == emp_id][
            ["date", "weekday", "status", "status_label", "paid_fraction", "day_earning", "ot_hours",
             "ot_pay", "total_earning"]]
        st.dataframe(dd, hide_index=True, column_config=col_cfg(dd))

# ---- 6. exports -----------------------------------------------------------
with tabs[5]:
    scope = st.radio("Include", [f"Filtered employees ({len(pay)})", f"All employees ({len(pay_all)})"],
                     horizontal=True, key="scope")
    sel = pay if scope.startswith("Filtered") else pay_all
    sel_ids = list(sel["employee_id"])
    fp = fingerprint(files and [(n, len(b)) for n, b in files], settings_key, codes, sel_ids)
    tag = f"{s.year}-{s.month:02d}"
    if not sel_ids:
        st.info("No employees to export – adjust the filters.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📊 Consolidated Excel report")
            st.caption("Summary, salary register, attendance summary & day-wise register, daily wages, "
                       "employee master and validation log – one formatted workbook.")
            lazy_download("Excel report", "xlsx", fp,
                          lambda: build_consolidated_workbook(result, data.issues, sel),
                          f"Payroll_Report_{tag}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown("##### 🗓️ Attendance report (PDF)")
            lazy_download("attendance PDF", "att_pdf", fp, lambda: attendance_report_pdf(result, sel),
                          f"Attendance_Report_{tag}.pdf", "application/pdf")
        with c2:
            st.markdown("##### 📄 Individual salary statements")
            st.caption("A ZIP file with one PDF per employee, or a single PDF for printing.")
            lazy_download(f"{len(sel_ids)} PDFs (ZIP)", "zip", fp, lambda: statements_zip(result, sel_ids),
                          f"Salary_Statements_{tag}.zip", "application/zip")
            lazy_download("combined PDF for printing", "all_pdf", fp,
                          lambda: all_statements_pdf(result, sel_ids),
                          safe_filename(f"Salary_Statements_{tag}_all") + ".pdf", "application/pdf")
