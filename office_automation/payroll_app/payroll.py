"""Daily wage and monthly payment calculations.

Rules (all configurable through :class:`~payroll_app.config.Settings`):

* **Daily wage** – taken from the ``Daily Wage`` column; if only a
  ``Monthly Salary`` is given it is converted as ``salary / divisor`` where the
  divisor is either the days in the month or a fixed number (default 26).
* **Day earning** – ``daily wage x paid fraction`` of the day's status
  (P = 1, HD = 0.5, paid leave / holiday / weekly-off = 1, A / LWP = 0).
* **Overtime pay** – ``OT hours x (daily wage / standard hours) x OT multiplier``.
* **Gross pay** – day earnings + overtime pay + fixed monthly allowance.
* **Net pay** – gross pay - fixed monthly deductions.
* **Attendance %** – days worked / scheduled working days (recorded days
  excluding holidays and weekly-offs).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import Settings
from .importer import ImportResult
from .validation import IssueLog


def _money(x: float) -> float:
    # round-half-up to 2 decimals (avoids banker's rounding surprises on payslips)
    return float(int(abs(x) * 100 + 0.5 + 1e-9) / 100) * (1 if x >= 0 else -1)


DAILY_COLUMNS = [
    "employee_id", "name", "department", "designation", "date", "weekday", "status",
    "status_label", "paid_fraction", "worked_fraction", "daily_wage", "day_earning",
    "ot_hours", "ot_pay", "total_earning",
]

PAYROLL_COLUMNS = [
    "employee_id", "name", "department", "designation", "wage_basis", "daily_wage",
    "days_in_month", "recorded_days", "present", "half_days", "paid_leave", "holidays",
    "weekly_off", "absent", "leave_without_pay", "unrecorded_days", "worked_days",
    "paid_days", "attendance_pct", "ot_hours", "basic_earnings", "ot_pay", "allowance",
    "gross_pay", "deduction", "net_pay", "bank_account",
]


@dataclass
class PayrollResult:
    employees: pd.DataFrame
    daily: pd.DataFrame
    payroll: pd.DataFrame
    attendance_summary: pd.DataFrame
    attendance_matrix: pd.DataFrame
    department_summary: pd.DataFrame
    issues: IssueLog
    settings: Settings

    @property
    def totals(self) -> dict[str, float]:
        p = self.payroll
        if p.empty:
            return {"employees": 0, "gross_pay": 0.0, "net_pay": 0.0, "ot_pay": 0.0,
                    "deduction": 0.0, "avg_attendance": 0.0}
        return {
            "employees": int(len(p)),
            "gross_pay": _money(p["gross_pay"].sum()),
            "net_pay": _money(p["net_pay"].sum()),
            "ot_pay": _money(p["ot_pay"].sum()),
            "deduction": _money(p["deduction"].sum()),
            "avg_attendance": round(float(p["attendance_pct"].mean()), 1),
        }


def exact_daily_rate(row: pd.Series, settings: Settings) -> float:
    """Unrounded daily rate (monthly salary / divisor for salaried staff)."""
    dw = row.get("daily_wage")
    if dw is not None and not pd.isna(dw):
        return float(dw)
    return float(row["monthly_salary"]) / settings.divisor()


def effective_daily_wage(row: pd.Series, settings: Settings) -> tuple[float, str]:
    dw = row.get("daily_wage")
    if dw is not None and not pd.isna(dw):
        return _money(float(dw)), "Daily wage"
    ms = float(row["monthly_salary"])
    div = settings.divisor()
    return _money(ms / div), f"Monthly {settings.currency} {ms:,.2f} / {div:g} days"


def _spread(values: list[float]) -> list[float]:
    """Round a list of amounts so the rounded items add up to the rounded total.

    Each item is the difference of the rounded running totals, so it is never
    more than one paisa/cent away from its exact value. Example: 31 days of
    45,000 / 31 = 1,451.6129... sum to exactly 45,000.00 instead of 44,999.91.
    """
    out, prev, run = [], 0, 0.0
    for v in values:
        run += v
        cents = int(round(_money(run) * 100))
        out.append((cents - prev) / 100)
        prev = cents
    return out


def compute_daily_wages(emp: pd.DataFrame, att: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    if emp.empty or att.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)
    exact = {r.employee_id: exact_daily_rate(r, settings) for _, r in emp.iterrows()}
    shown = {r.employee_id: effective_daily_wage(r, settings)[0] for _, r in emp.iterrows()}
    info = emp.set_index("employee_id")[["name", "department", "designation"]]
    df = att.merge(info, left_on="employee_id", right_index=True, how="inner").copy()
    df = df.sort_values(["employee_id", "date"]).reset_index(drop=True)
    codes = settings.status_codes
    df["status_label"] = df["status"].map(lambda c: codes[c].label)
    df["paid_fraction"] = df["status"].map(lambda c: codes[c].paid)
    df["worked_fraction"] = df["status"].map(lambda c: codes[c].worked)
    df["daily_wage"] = df["employee_id"].map(shown)
    df["weekday"] = pd.to_datetime(df["date"]).dt.strftime("%a")
    rate = df["employee_id"].map(exact)
    day_exact = (rate * df["paid_fraction"]).tolist()
    ot_exact = (df["ot_hours"] * rate / settings.standard_hours * settings.overtime_multiplier).tolist()
    day_earn, ot_pay = [0.0] * len(df), [0.0] * len(df)
    for _, idx in df.groupby("employee_id", sort=False).indices.items():
        for i, v in zip(idx, _spread([day_exact[i] for i in idx])):
            day_earn[i] = v
        for i, v in zip(idx, _spread([ot_exact[i] for i in idx])):
            ot_pay[i] = v
    df["day_earning"] = day_earn
    df["ot_pay"] = ot_pay
    df["total_earning"] = [_money(a + b) for a, b in zip(df["day_earning"], df["ot_pay"])]
    return df[DAILY_COLUMNS]


def compute_payroll(data: ImportResult, settings: Settings | None = None) -> PayrollResult:
    settings = settings or data.settings
    log = IssueLog()
    emp, att = data.employees, data.attendance
    daily = compute_daily_wages(emp, att, settings)

    rows = []
    for _, e in emp.iterrows():
        dw, basis = effective_daily_wage(e, settings)
        d = daily[daily["employee_id"] == e.employee_id]
        counts = d["status"].value_counts().to_dict()
        recorded = int(len(d))
        hol = counts.get("H", 0)
        wo = counts.get("WO", 0)
        worked = float(d["worked_fraction"].sum())
        paid = float(d["paid_fraction"].sum())
        scheduled = recorded - hol - wo
        att_pct = round(worked / scheduled * 100, 1) if scheduled > 0 else 0.0
        extra_ot = 0.0
        if not data.extra_overtime.empty:
            extra_ot = float(data.extra_overtime.loc[
                data.extra_overtime["employee_id"] == e.employee_id, "ot_hours"].sum())
        ot_hours = float(d["ot_hours"].sum()) + extra_ot
        basic = _money(d["day_earning"].sum())
        rate = exact_daily_rate(e, settings)
        ot_pay = _money(d["ot_pay"].sum() + extra_ot * rate / settings.standard_hours * settings.overtime_multiplier)
        allowance = _money(float(e.get("allowance") or 0))
        deduction = _money(float(e.get("deduction") or 0))
        if recorded == 0:
            allowance = 0.0  # nothing worked this period -> no fixed allowance either
        gross = _money(basic + ot_pay + allowance)
        net = _money(gross - deduction)
        if net < 0:
            log.warning(f"Deductions ({deduction:,.2f}) exceed gross pay ({gross:,.2f}); "
                        f"net pay is negative", employee_id=e.employee_id)
        if paid > settings.days_in_month:
            log.error("More paid days than days in the month – check attendance",
                      employee_id=e.employee_id)
        rows.append({
            "employee_id": e.employee_id, "name": e["name"], "department": e["department"],
            "designation": e["designation"], "wage_basis": basis, "daily_wage": dw,
            "days_in_month": settings.days_in_month, "recorded_days": recorded,
            "present": counts.get("P", 0), "half_days": counts.get("HD", 0),
            "paid_leave": counts.get("L", 0), "holidays": hol, "weekly_off": wo,
            "absent": counts.get("A", 0), "leave_without_pay": counts.get("LWP", 0),
            "unrecorded_days": settings.days_in_month - recorded,
            "worked_days": worked, "paid_days": paid, "attendance_pct": att_pct,
            "ot_hours": round(ot_hours, 2), "basic_earnings": basic, "ot_pay": ot_pay,
            "allowance": allowance, "gross_pay": gross, "deduction": deduction,
            "net_pay": net, "bank_account": e.get("bank_account", ""),
        })
    payroll = pd.DataFrame(rows, columns=PAYROLL_COLUMNS)

    att_summary = payroll[[
        "employee_id", "name", "department", "recorded_days", "present", "half_days",
        "paid_leave", "holidays", "weekly_off", "absent", "leave_without_pay",
        "unrecorded_days", "worked_days", "paid_days", "ot_hours", "attendance_pct",
    ]].copy()

    matrix = build_attendance_matrix(emp, daily, settings)
    dept = department_summary(payroll)
    return PayrollResult(emp, daily, payroll, att_summary, matrix, dept, log, settings)


def build_attendance_matrix(emp: pd.DataFrame, daily: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    days = list(range(1, settings.days_in_month + 1))
    base = emp[["employee_id", "name", "department"]].copy() if not emp.empty else \
        pd.DataFrame(columns=["employee_id", "name", "department"])
    if daily.empty:
        for d in days:
            base[d] = ""
        return base
    piv = daily.assign(day=pd.to_datetime(daily["date"]).dt.day).pivot_table(
        index="employee_id", columns="day", values="status", aggfunc="last")
    piv = piv.reindex(columns=days)
    out = base.merge(piv, left_on="employee_id", right_index=True, how="left")
    out[days] = out[days].fillna("")
    return out


def department_summary(payroll: pd.DataFrame) -> pd.DataFrame:
    cols = ["department", "employees", "paid_days", "ot_hours", "gross_pay", "deduction",
            "net_pay", "avg_attendance_pct"]
    if payroll.empty:
        return pd.DataFrame(columns=cols)
    g = payroll.groupby("department", sort=True).agg(
        employees=("employee_id", "count"), paid_days=("paid_days", "sum"),
        ot_hours=("ot_hours", "sum"), gross_pay=("gross_pay", "sum"),
        deduction=("deduction", "sum"), net_pay=("net_pay", "sum"),
        avg_attendance_pct=("attendance_pct", "mean"),
    ).reset_index()
    for c in ("gross_pay", "deduction", "net_pay"):
        g[c] = g[c].map(_money)
    g["avg_attendance_pct"] = g["avg_attendance_pct"].round(1)
    return g[cols]
