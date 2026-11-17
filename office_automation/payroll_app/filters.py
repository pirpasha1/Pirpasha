"""Search and filter helpers shared by the UI, the CLI and the tests."""
from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


def search_mask(df: pd.DataFrame, text: str,
                columns: Iterable[str] = ("employee_id", "name", "department", "designation")) -> pd.Series:
    """Case-insensitive 'contains' search over several columns.

    Several words are AND-ed: ``"ravi stores"`` finds Ravi in the Stores dept.
    """
    mask = pd.Series(True, index=df.index)
    words = [w for w in str(text or "").lower().split() if w]
    if not words or df.empty:
        return mask
    cols = [c for c in columns if c in df.columns]
    hay = df[cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    for w in words:
        mask &= hay.str.contains(w, regex=False)
    return mask


def filter_payroll(df: pd.DataFrame, search: str = "", departments: Iterable[str] | None = None,
                   designations: Iterable[str] | None = None,
                   min_attendance: float | None = None, max_attendance: float | None = None,
                   min_net: float | None = None, max_net: float | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    mask = search_mask(df, search)
    if departments:
        mask &= df["department"].isin(list(departments))
    if designations:
        mask &= df["designation"].isin(list(designations))
    if "attendance_pct" in df.columns:
        if min_attendance is not None:
            mask &= df["attendance_pct"] >= min_attendance
        if max_attendance is not None:
            mask &= df["attendance_pct"] <= max_attendance
    if "net_pay" in df.columns:
        if min_net is not None:
            mask &= df["net_pay"] >= min_net
        if max_net is not None:
            mask &= df["net_pay"] <= max_net
    return df[mask].reset_index(drop=True)


def filter_daily(df: pd.DataFrame, search: str = "", employee_ids: Iterable[str] | None = None,
                 statuses: Iterable[str] | None = None, start: date | None = None,
                 end: date | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    mask = search_mask(df, search)
    if employee_ids:
        mask &= df["employee_id"].isin(list(employee_ids))
    if statuses:
        mask &= df["status"].isin(list(statuses))
    if start is not None:
        mask &= df["date"] >= start
    if end is not None:
        mask &= df["date"] <= end
    return df[mask].reset_index(drop=True)
