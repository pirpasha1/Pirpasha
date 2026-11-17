"""Application settings and attendance status codes."""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class StatusCode:
    code: str
    label: str
    worked: float  # fraction of a day physically worked (for attendance %)
    paid: float  # fraction of a day that is paid


# Default attendance codes. Keys are upper-case; aliases map onto them.
DEFAULT_STATUS_CODES: dict[str, StatusCode] = {
    "P": StatusCode("P", "Present", 1.0, 1.0),
    "A": StatusCode("A", "Absent", 0.0, 0.0),
    "HD": StatusCode("HD", "Half Day", 0.5, 0.5),
    "L": StatusCode("L", "Paid Leave", 0.0, 1.0),
    "LWP": StatusCode("LWP", "Leave Without Pay", 0.0, 0.0),
    "H": StatusCode("H", "Holiday", 0.0, 1.0),
    "WO": StatusCode("WO", "Weekly Off", 0.0, 1.0),
}

STATUS_ALIASES: dict[str, str] = {
    "PRESENT": "P", "1": "P", "Y": "P", "YES": "P",
    "ABSENT": "A", "0": "A", "N": "A", "NO": "A", "AB": "A",
    "HALF": "HD", "HALF DAY": "HD", "HALFDAY": "HD", "H/D": "HD", "0.5": "HD", "½": "HD",
    "LEAVE": "L", "PL": "L", "CL": "L", "SL": "L", "EL": "L", "PAID LEAVE": "L",
    "UL": "LWP", "UNPAID": "LWP", "UNPAID LEAVE": "LWP", "LOP": "LWP",
    "HOLIDAY": "H", "PH": "H", "GH": "H",
    "OFF": "WO", "W/O": "WO", "WEEKLY OFF": "WO", "SUNDAY": "WO",
}


@dataclass
class Settings:
    company_name: str = "My Company Pvt. Ltd."
    year: int = field(default_factory=lambda: date.today().year)
    month: int = field(default_factory=lambda: date.today().month)
    currency: str = "Rs."
    # How a monthly salary is converted into a daily wage:
    #   "calendar" -> divide by the number of days in the month
    #   a number   -> fixed divisor (e.g. 26 working days). If you use 26,
    #                 set the paid fraction of WO (weekly off) to 0, otherwise
    #                 a full month pays more than the monthly salary.
    monthly_divisor: str | int = "calendar"
    standard_hours: float = 8.0  # hours in a normal working day
    overtime_multiplier: float = 2.0  # OT hourly rate = hourly wage x multiplier
    max_overtime_hours: float = 12.0  # per day; above this is flagged
    status_codes: dict[str, StatusCode] = field(
        default_factory=lambda: dict(DEFAULT_STATUS_CODES)
    )

    def __post_init__(self) -> None:
        if not 1 <= int(self.month) <= 12:
            raise ValueError(f"Month must be between 1 and 12, got {self.month}")
        if not 1900 <= int(self.year) <= 2200:
            raise ValueError(f"Year looks invalid: {self.year}")
        if self.standard_hours <= 0:
            raise ValueError("Standard hours per day must be greater than zero")
        if self.overtime_multiplier < 0:
            raise ValueError("Overtime multiplier cannot be negative")
        if self.monthly_divisor != "calendar":
            try:
                d = float(self.monthly_divisor)
            except (TypeError, ValueError):
                raise ValueError(
                    "Monthly divisor must be 'calendar' or a number of days"
                ) from None
            if not 1 <= d <= 31:
                raise ValueError("Monthly divisor must be between 1 and 31 days")

    # ---- period helpers -------------------------------------------------
    @property
    def days_in_month(self) -> int:
        return calendar.monthrange(int(self.year), int(self.month))[1]

    @property
    def period_start(self) -> date:
        return date(int(self.year), int(self.month), 1)

    @property
    def period_end(self) -> date:
        return date(int(self.year), int(self.month), self.days_in_month)

    @property
    def period_label(self) -> str:
        return self.period_start.strftime("%B %Y")

    def divisor(self) -> float:
        if self.monthly_divisor == "calendar":
            return float(self.days_in_month)
        return float(self.monthly_divisor)

    def normalise_status(self, raw: object) -> str | None:
        """Return the canonical status code for *raw* or ``None`` if unknown."""
        if raw is None:
            return None
        if isinstance(raw, float):
            if raw != raw:  # NaN
                return None
            raw = int(raw) if raw.is_integer() else raw
        text = str(raw).strip().upper()
        if not text:
            return None
        if text in self.status_codes:
            return text
        alias = STATUS_ALIASES.get(text)
        if alias and alias in self.status_codes:
            return alias
        return None
