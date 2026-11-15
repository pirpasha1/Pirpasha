"""Convert an amount to words (Indian numbering: thousand, lakh, crore)."""
from __future__ import annotations

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
         "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + " " + _ONES[n % 10]).strip()


def _below_1000(n: int) -> str:
    h, rest = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " Hundred")
    if rest:
        parts.append(_below_100(rest))
    return " ".join(parts)


def integer_to_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append(integer_to_words(crore) + " Crore")
    if lakh:
        parts.append(_below_100(lakh) + " Lakh")
    if thousand:
        parts.append(_below_100(thousand) + " Thousand")
    if n:
        parts.append(_below_1000(n))
    return " ".join(parts)


def amount_in_words(amount: float, currency: str = "Rs.") -> str:
    major, minor = ("Rupees", "Paise") if currency.strip().upper().rstrip(".") in {"RS", "INR", "₹"} \
        else (currency.strip(), "Cents")
    negative = amount < 0
    cents = int(round(abs(amount) * 100))
    whole, frac = divmod(cents, 100)
    text = f"{major} {integer_to_words(whole)}"
    if frac:
        text += f" and {integer_to_words(frac)} {minor}"
    text += " Only"
    return ("Minus " + text) if negative else text
