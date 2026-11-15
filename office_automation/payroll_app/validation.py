"""Collects errors / warnings found while importing and calculating."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

import pandas as pd

ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"


@dataclass
class Issue:
    severity: str
    message: str
    file: str = ""
    sheet: str = ""
    row: int | None = None  # Excel row number (1-based, header = row 1)
    employee_id: str = ""


class IssueLog:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def add(self, severity: str, message: str, **ctx) -> None:
        self.issues.append(Issue(severity, message, **ctx))

    def error(self, message: str, **ctx) -> None:
        self.add(ERROR, message, **ctx)

    def warning(self, message: str, **ctx) -> None:
        self.add(WARNING, message, **ctx)

    def info(self, message: str, **ctx) -> None:
        self.add(INFO, message, **ctx)

    def extend(self, other: "IssueLog | Iterable[Issue]") -> None:
        self.issues.extend(other.issues if isinstance(other, IssueLog) else other)

    def count(self, severity: str) -> int:
        return sum(1 for i in self.issues if i.severity == severity)

    @property
    def has_errors(self) -> bool:
        return self.count(ERROR) > 0

    def to_frame(self) -> pd.DataFrame:
        cols = ["severity", "message", "file", "sheet", "row", "employee_id"]
        if not self.issues:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame([asdict(i) for i in self.issues], columns=cols)
        df["row"] = df["row"].astype("Int64")
        order = {ERROR: 0, WARNING: 1, INFO: 2}
        return df.sort_values(
            by="severity", key=lambda s: s.map(order), kind="stable"
        ).reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.issues)
