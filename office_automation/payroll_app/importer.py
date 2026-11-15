"""Import employee records and attendance from any number of Excel files.

Every sheet of every workbook is inspected and classified automatically:

* **Employee master** – has an employee ID, a name and a wage column
  (``Daily Wage`` or ``Monthly Salary``).
* **Attendance (long / register format)** – one row per employee per day with
  ``Employee ID``, ``Date`` and ``Status`` (optional ``OT Hours``).
* **Attendance (wide / muster-roll format)** – one row per employee with one
  column per day (``1`` .. ``31`` or real dates) holding status codes.

A sheet can be both a master and a muster roll (e.g. a muster roll that also
carries a ``Daily Wage`` column).  Column headers are matched case-insensitively
against a list of common aliases, and a title block above the header row is
skipped automatically.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO, Iterable, Union

import pandas as pd

from .config import Settings
from .validation import IssueLog

Source = Union[str, Path, tuple[str, Union[bytes, BinaryIO]]]

COLUMN_ALIASES: dict[str, list[str]] = {
    "employee_id": [
        "employee id", "emp id", "empid", "employee code", "emp code",
        "employee no", "emp no", "employee number", "staff id", "staff no",
        "id", "code", "token no", "e code", "ecode",
    ],
    "name": ["employee name", "name", "emp name", "full name", "staff name", "worker name"],
    "department": ["department", "dept", "division", "section", "unit"],
    "designation": ["designation", "role", "position", "job title", "title", "grade"],
    "daily_wage": [
        "daily wage", "daily wages", "daily rate", "wage per day", "per day wage",
        "rate per day", "day rate", "wage rate", "per day rate",
    ],
    "monthly_salary": [
        "monthly salary", "salary", "basic salary", "monthly wage", "basic",
        "gross salary", "salary per month", "monthly pay",
    ],
    "allowance": ["allowance", "allowances", "other allowance", "other allowances", "bonus", "incentive"],
    "deduction": ["deduction", "deductions", "other deduction", "other deductions", "advance", "loan recovery"],
    "bank_account": ["bank account", "bank a/c", "account no", "account number", "a/c no", "bank account no"],
    "date": ["date", "attendance date", "work date", "day date"],
    "status": ["status", "attendance", "attendance status", "mark", "present/absent", "p/a"],
    "ot_hours": ["ot hours", "ot", "overtime", "overtime hours", "extra hours", "ot hrs", "total ot"],
}

EMPLOYEE_COLUMNS = [
    "employee_id", "name", "department", "designation", "daily_wage",
    "monthly_salary", "allowance", "deduction", "bank_account", "source",
]
ATTENDANCE_COLUMNS = ["employee_id", "date", "status", "ot_hours", "source"]
OVERTIME_COLUMNS = ["employee_id", "ot_hours", "source"]

MAX_HEADER_SCAN_ROWS = 15
MIN_DAY_COLUMNS = 5


@dataclass
class ImportResult:
    employees: pd.DataFrame
    attendance: pd.DataFrame
    extra_overtime: pd.DataFrame  # monthly OT totals from muster-roll sheets
    issues: IssueLog
    files: pd.DataFrame  # one row per file/sheet with what was found
    settings: Settings = field(repr=False, default=None)  # type: ignore[assignment]

    @property
    def ok(self) -> bool:
        return not self.employees.empty


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _norm_header(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[_\-\.:#()]+", " ", text)
    text = text.replace("/ ", "/").replace(" /", "/")
    return re.sub(r"\s+", " ", text).strip()


_ALIAS_LOOKUP: dict[str, str] = {}
for _canon, _aliases in COLUMN_ALIASES.items():
    for _a in _aliases:
        _ALIAS_LOOKUP[_norm_header(_a)] = _canon


def _match_column(header: object) -> str | None:
    if header is None or (isinstance(header, float) and pd.isna(header)):
        return None
    if isinstance(header, (datetime, date, pd.Timestamp)):
        return None
    return _ALIAS_LOOKUP.get(_norm_header(header))


def normalise_employee_id(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if pd.isna(value):
            return ""
        if value.is_integer():
            value = int(value)
    text = str(value).strip().upper()
    return "" if text in {"NAN", "NONE", "NULL"} else text


def _to_number(value: object) -> float | None:
    """Parse numbers like ``1,250.50`` / ``Rs. 500`` / ``₹ 600``. ``None`` if blank/invalid."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"(?i)^(rs\.?|inr|₹|\$|usd)\s*", "", text).replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return isinstance(value, str) and not value.strip()


def _to_date(value: object) -> date | None:
    if _is_blank(value):
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        # Excel serial date number
        if 20000 < float(value) < 80000:
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(value))).date()
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(text, dayfirst=True, errors="raise")
        return ts.date()
    except (ValueError, TypeError, OverflowError):
        return None


def _day_column_date(header: object, settings: Settings) -> date | None:
    """Interpret a muster-roll column header as a day of the pay period."""
    if isinstance(header, (pd.Timestamp, datetime, date)):
        return _to_date(header)
    if isinstance(header, bool) or _is_blank(header):
        return None
    day: int | None = None
    if isinstance(header, (int, float)) and float(header).is_integer():
        day = int(header)
    else:
        text = str(header).strip()
        m = re.fullmatch(r"(?i)(?:day\s*)?(\d{1,2})", text)
        if m:
            day = int(m.group(1))
        elif re.search(r"\d", text) and re.search(r"[-/ ]", text):
            return _to_date(text)
    if day is not None and 1 <= day <= 31:
        if day > settings.days_in_month:
            return None
        return date(settings.year, settings.month, day)
    return None


def _read_workbook(source: Source) -> tuple[str, dict[str, pd.DataFrame]]:
    if isinstance(source, tuple):
        name, data = source
        buf = io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data
    else:
        name, buf = Path(source).name, source
    lower = name.lower()
    if not lower.endswith((".xlsx", ".xlsm", ".xls")):
        raise ValueError("Not an Excel file (expected .xlsx, .xlsm or .xls)")
    engine = "xlrd" if lower.endswith(".xls") else "openpyxl"
    sheets = pd.read_excel(buf, sheet_name=None, header=None, engine=engine, dtype=object)
    return name, sheets


def _locate_header(raw: pd.DataFrame) -> int | None:
    """Return the index of the row that looks like the header row."""
    best_row, best_score = None, 0
    for idx in range(min(MAX_HEADER_SCAN_ROWS, len(raw))):
        mapped = {_match_column(v) for v in raw.iloc[idx].tolist()} - {None}
        if "employee_id" not in mapped:
            continue
        score = len(mapped)
        if score > best_score:
            best_row, best_score = idx, score
    return best_row


# --------------------------------------------------------------------------
# sheet parsers
# --------------------------------------------------------------------------
def _parse_employees(rows, colmap, ctx, log: IssueLog) -> list[dict]:
    out = []
    for excel_row, row in rows:
        emp_id = normalise_employee_id(row.get(colmap["employee_id"]))
        if not emp_id:
            if any(not _is_blank(v) for v in row.values()):
                log.error("Missing employee ID – row skipped", row=excel_row, **ctx)
            continue
        rec = {"employee_id": emp_id, "source": f"{ctx['file']} / {ctx['sheet']} (row {excel_row})"}
        name = row.get(colmap.get("name")) if "name" in colmap else None
        if _is_blank(name):
            log.warning("Employee name is blank", row=excel_row, employee_id=emp_id, **ctx)
            name = ""
        name = re.sub(r"\s+", " ", str(name)).strip()
        if name.isupper() or name.islower():  # "RAVI KUMAR" / "ravi kumar" -> "Ravi Kumar"
            name = name.title()
        rec["name"] = name or "(No name)"
        for col in ("department", "designation", "bank_account"):
            val = row.get(colmap[col]) if col in colmap else None
            rec[col] = "" if _is_blank(val) else re.sub(r"\s+", " ", str(val)).strip()
            if col == "bank_account" and isinstance(val, float) and val.is_integer():
                rec[col] = str(int(val))
        if not rec["department"]:
            rec["department"] = "Unassigned"

        for col in ("daily_wage", "monthly_salary"):
            raw = row.get(colmap[col]) if col in colmap else None
            num = _to_number(raw)
            if not _is_blank(raw) and num is None:
                log.error(f"{col.replace('_', ' ').title()} '{raw}' is not a number",
                          row=excel_row, employee_id=emp_id, **ctx)
            elif num is not None and num <= 0:
                log.error(f"{col.replace('_', ' ').title()} must be greater than zero (found {num:g})",
                          row=excel_row, employee_id=emp_id, **ctx)
                num = None
            rec[col] = num
        if rec["daily_wage"] is None and rec["monthly_salary"] is None:
            log.error("No valid daily wage or monthly salary – employee skipped",
                      row=excel_row, employee_id=emp_id, **ctx)
            continue
        if rec["daily_wage"] is not None and rec["daily_wage"] > 100000:
            log.warning(f"Daily wage {rec['daily_wage']:,.2f} is unusually high – please verify",
                        row=excel_row, employee_id=emp_id, **ctx)

        for col in ("allowance", "deduction"):
            raw = row.get(colmap[col]) if col in colmap else None
            num = _to_number(raw)
            if not _is_blank(raw) and num is None:
                log.warning(f"{col.title()} '{raw}' is not a number – treated as 0",
                            row=excel_row, employee_id=emp_id, **ctx)
                num = 0.0
            if num is not None and num < 0:
                log.warning(f"Negative {col} ({num:g}) – treated as 0",
                            row=excel_row, employee_id=emp_id, **ctx)
                num = 0.0
            rec[col] = num or 0.0
        out.append(rec)
    return out


def _parse_status(raw, settings: Settings, log: IssueLog, excel_row, emp_id, ctx, where=""):
    code = settings.normalise_status(raw)
    if code is None:
        log.error(f"Unknown attendance status '{raw}'{where} – entry skipped "
                  f"(valid codes: {', '.join(settings.status_codes)})",
                  row=excel_row, employee_id=emp_id, **ctx)
    return code


def _parse_long_attendance(rows, colmap, ctx, settings: Settings, log: IssueLog):
    out, outside = [], 0
    for excel_row, row in rows:
        emp_id = normalise_employee_id(row.get(colmap["employee_id"]))
        raw_date, raw_status = row.get(colmap["date"]), row.get(colmap["status"])
        if not emp_id:
            if any(not _is_blank(v) for v in row.values()):
                log.error("Missing employee ID – attendance row skipped", row=excel_row, **ctx)
            continue
        d = _to_date(raw_date)
        if d is None:
            log.error(f"Invalid or missing date '{'' if _is_blank(raw_date) else raw_date}' – row skipped",
                      row=excel_row, employee_id=emp_id, **ctx)
            continue
        if not settings.period_start <= d <= settings.period_end:
            outside += 1
            continue
        if _is_blank(raw_status):
            log.warning(f"Blank attendance status on {d:%d-%b-%Y} – day left unrecorded",
                        row=excel_row, employee_id=emp_id, **ctx)
            continue
        code = _parse_status(raw_status, settings, log, excel_row, emp_id, ctx)
        if code is None:
            continue
        ot = 0.0
        if "ot_hours" in colmap:
            raw_ot = row.get(colmap["ot_hours"])
            ot_num = _to_number(raw_ot)
            if not _is_blank(raw_ot) and ot_num is None:
                log.warning(f"OT hours '{raw_ot}' is not a number – treated as 0",
                            row=excel_row, employee_id=emp_id, **ctx)
            elif ot_num is not None and ot_num < 0:
                log.warning(f"Negative OT hours ({ot_num:g}) – treated as 0",
                            row=excel_row, employee_id=emp_id, **ctx)
            elif ot_num is not None:
                ot = ot_num
                if ot > settings.max_overtime_hours:
                    log.warning(f"{ot:g} OT hours on {d:%d-%b-%Y} exceeds the limit of "
                                f"{settings.max_overtime_hours:g} – please verify",
                                row=excel_row, employee_id=emp_id, **ctx)
            if ot > 0 and settings.status_codes[code].worked == 0:
                log.warning(f"OT hours recorded on a non-working day ({code}) on {d:%d-%b-%Y} – OT ignored",
                            row=excel_row, employee_id=emp_id, **ctx)
                ot = 0.0
        out.append({"employee_id": emp_id, "date": d, "status": code, "ot_hours": ot,
                    "source": f"{ctx['file']} / {ctx['sheet']} (row {excel_row})"})
    if outside:
        log.info(f"{outside} attendance row(s) dated outside {settings.period_label} were ignored", **ctx)
    return out


def _parse_wide_attendance(rows, colmap, day_cols, ctx, settings: Settings, log: IssueLog):
    out, ot_rows = [], []
    for excel_row, row in rows:
        emp_id = normalise_employee_id(row.get(colmap["employee_id"]))
        if not emp_id:
            if any(not _is_blank(row.get(c)) for c in day_cols):
                log.error("Missing employee ID – muster-roll row skipped", row=excel_row, **ctx)
            continue
        for col, d in day_cols.items():
            raw = row.get(col)
            if _is_blank(raw):
                continue
            code = _parse_status(raw, settings, log, excel_row, emp_id, ctx, where=f" on {d:%d-%b-%Y}")
            if code is None:
                continue
            out.append({"employee_id": emp_id, "date": d, "status": code, "ot_hours": 0.0,
                        "source": f"{ctx['file']} / {ctx['sheet']} (row {excel_row})"})
        if "ot_hours" in colmap:
            raw_ot = row.get(colmap["ot_hours"])
            ot = _to_number(raw_ot)
            if not _is_blank(raw_ot) and (ot is None or ot < 0):
                log.warning(f"Invalid monthly OT hours '{raw_ot}' – treated as 0",
                            row=excel_row, employee_id=emp_id, **ctx)
            elif ot:
                ot_rows.append({"employee_id": emp_id, "ot_hours": ot,
                                "source": f"{ctx['file']} / {ctx['sheet']} (row {excel_row})"})
    return out, ot_rows


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def import_files(sources: Iterable[Source], settings: Settings) -> ImportResult:
    """Read every sheet of every file and return clean, validated tables."""
    log = IssueLog()
    employees: list[dict] = []
    attendance: list[dict] = []
    extra_ot: list[dict] = []
    summary: list[dict] = []
    sources = list(sources)
    if not sources:
        log.error("No files were provided")

    for source in sources:
        display = source[0] if isinstance(source, tuple) else Path(source).name
        try:
            fname, sheets = _read_workbook(source)
        except Exception as exc:  # corrupt / wrong type / missing file
            log.error(f"Could not read file: {exc}", file=display)
            summary.append({"file": display, "sheet": "-", "detected_as": "UNREADABLE", "rows": 0})
            continue
        for sheet_name, raw in sheets.items():
            ctx = {"file": fname, "sheet": str(sheet_name)}
            raw = raw.dropna(how="all").dropna(axis=1, how="all")
            if raw.empty:
                log.info("Empty sheet ignored", **ctx)
                summary.append({**ctx, "detected_as": "empty", "rows": 0})
                continue
            raw = raw.reset_index(drop=True)
            header_idx = _locate_header(raw)
            if header_idx is None:
                log.warning("No 'Employee ID' column found – sheet skipped", **ctx)
                summary.append({**ctx, "detected_as": "not recognised", "rows": 0})
                continue
            headers = raw.iloc[header_idx].tolist()
            colmap: dict[str, int] = {}
            day_cols: dict[int, date] = {}
            for pos, h in enumerate(headers):
                canon = _match_column(h)
                if canon and canon not in colmap:
                    colmap[canon] = pos
                elif canon is None:
                    d = _day_column_date(h, settings)
                    if d is not None and settings.period_start <= d <= settings.period_end:
                        day_cols[pos] = d
            # Excel row numbers: header row + offset of dropped leading blank rows isn't
            # tracked after dropna, so compute from the original index instead.
            data = raw.iloc[header_idx + 1:]
            orig_index = sheets[sheet_name].dropna(how="all").index
            rows = []
            for i, (_, r) in enumerate(data.iterrows()):
                excel_row = int(orig_index[header_idx + 1 + i]) + 1
                rows.append((excel_row, {pos: r.iloc[pos] for pos in range(len(headers))}))

            kinds = []
            is_master = "name" in colmap and ("daily_wage" in colmap or "monthly_salary" in colmap)
            is_long = "date" in colmap and "status" in colmap
            is_wide = len(day_cols) >= MIN_DAY_COLUMNS
            if is_master:
                recs = _parse_employees(rows, colmap, ctx, log)
                employees.extend(recs)
                kinds.append(f"employees ({len(recs)})")
            if is_long:
                recs = _parse_long_attendance(rows, colmap, ctx, settings, log)
                attendance.extend(recs)
                kinds.append(f"attendance ({len(recs)} entries)")
            elif is_wide:
                recs, ot = _parse_wide_attendance(rows, colmap, day_cols, ctx, settings, log)
                attendance.extend(recs)
                extra_ot.extend(ot)
                kinds.append(f"muster roll ({len(recs)} entries)")
            if not kinds:
                if "date" in colmap or "status" in colmap:
                    missing = [c for c in ("date", "status") if c not in colmap]
                    msg = f"Attendance sheet is missing column(s): {', '.join(missing)} – sheet skipped"
                elif "name" in colmap:
                    msg = "Employee sheet has no 'Daily Wage' or 'Monthly Salary' column – sheet skipped"
                else:
                    msg = ("Sheet not recognised – expected an employee list (ID, Name, Wage) or "
                           "attendance (ID, Date, Status or day columns 1-31) – sheet skipped")
                    # muster roll for a different month?
                    other_month = sum(1 for h in headers if _day_column_date(h, settings) is None
                                      and isinstance(h, (datetime, pd.Timestamp)))
                    if other_month >= MIN_DAY_COLUMNS:
                        msg = f"Muster-roll dates are not in {settings.period_label} – sheet skipped"
                log.warning(msg, **ctx)
                kinds.append("not recognised")
            summary.append({**ctx, "detected_as": ", ".join(kinds), "rows": len(rows)})

    emp_df = _dedupe_employees(employees, log)
    att_df = _dedupe_attendance(attendance, log)
    ot_df = pd.DataFrame(extra_ot, columns=OVERTIME_COLUMNS)
    _cross_check(emp_df, att_df, ot_df, settings, log)
    if emp_df.empty and sources:
        log.error("No valid employee records were found. At least one sheet must contain "
                  "Employee ID, Name and Daily Wage (or Monthly Salary) columns.")
    if not att_df.empty:
        att_df = att_df[att_df["employee_id"].isin(emp_df["employee_id"])].reset_index(drop=True)
    if not ot_df.empty:
        ot_df = ot_df[ot_df["employee_id"].isin(emp_df["employee_id"])].reset_index(drop=True)
    files_df = pd.DataFrame(summary, columns=["file", "sheet", "detected_as", "rows"])
    return ImportResult(emp_df, att_df, ot_df, log, files_df, settings)


def _dedupe_employees(records: list[dict], log: IssueLog) -> pd.DataFrame:
    df = pd.DataFrame(records, columns=EMPLOYEE_COLUMNS)
    if df.empty:
        return df
    compare = ["name", "department", "designation", "daily_wage", "monthly_salary", "allowance", "deduction"]
    keep_rows = []
    for emp_id, grp in df.groupby("employee_id", sort=False):
        first = grp.iloc[0]
        keep_rows.append(grp.index[0])
        for _, other in grp.iloc[1:].iterrows():
            same = all((pd.isna(first[c]) and pd.isna(other[c])) or first[c] == other[c] for c in compare)
            if same:
                log.info(f"Duplicate employee record in {other['source']} ignored (identical data)",
                         employee_id=emp_id)
            else:
                log.warning(f"Conflicting duplicate employee ID: {other['source']} differs from "
                            f"{first['source']}. The first record is used.", employee_id=emp_id)
    return df.loc[keep_rows].sort_values("employee_id", key=_natural_key).reset_index(drop=True)


def _natural_key(series: pd.Series) -> pd.Series:
    return series.map(lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))])


def _dedupe_attendance(records: list[dict], log: IssueLog) -> pd.DataFrame:
    df = pd.DataFrame(records, columns=ATTENDANCE_COLUMNS)
    if df.empty:
        return df
    dup_mask = df.duplicated(["employee_id", "date"], keep="last")
    for _, r in df[dup_mask].iterrows():
        later = df[(df.employee_id == r.employee_id) & (df.date == r.date)].iloc[-1]
        level = log.info if later.status == r.status and later.ot_hours == r.ot_hours else log.warning
        level(f"Duplicate attendance for {r.date:%d-%b-%Y}: entry from {r.source} replaced by "
              f"{later.source} ({r.status} -> {later.status})", employee_id=r.employee_id)
    df = df[~dup_mask]
    return df.sort_values(["employee_id", "date"]).reset_index(drop=True)


def _cross_check(emp_df, att_df, ot_df, settings: Settings, log: IssueLog) -> None:
    known = set(emp_df["employee_id"]) if not emp_df.empty else set()
    if not att_df.empty:
        unknown = att_df[~att_df["employee_id"].isin(known)]
        for emp_id, grp in unknown.groupby("employee_id"):
            log.warning(f"{len(grp)} attendance entr{'y' if len(grp) == 1 else 'ies'} for an employee "
                        f"not in any employee list – excluded from payroll", employee_id=emp_id)
    for emp_id in ot_df["employee_id"].unique() if not ot_df.empty else []:
        if emp_id not in known:
            log.warning("Monthly OT hours for an employee not in any employee list – ignored",
                        employee_id=emp_id)
    for emp_id in sorted(known):
        n = int((att_df["employee_id"] == emp_id).sum()) if not att_df.empty else 0
        if n == 0:
            log.warning(f"No attendance found for {settings.period_label} – no wages calculated",
                        employee_id=emp_id)
        elif n < settings.days_in_month:
            log.warning(f"Attendance recorded for {n} of {settings.days_in_month} days – "
                        f"{settings.days_in_month - n} day(s) unrecorded are not paid",
                        employee_id=emp_id)
