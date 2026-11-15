"""Display helpers: Indian-style currency grouping (lakh / crore) and units."""


def indian_group(n):
    """Group an integer the Indian way: 12345678 -> '1,23,45,678'."""
    sign = "-" if n < 0 else ""
    s = str(abs(int(round(n))))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups) + "," + tail


def inr(value, symbol="₹"):
    if value is None:
        return "—"
    return f"{symbol}{indian_group(value)}"


def inr_short(value, symbol="₹"):
    """₹1.12 Cr / ₹68.5 L style."""
    if value is None:
        return "—"
    if value >= 1e7:
        return f"{symbol}{value / 1e7:.2f} Cr"
    if value >= 1e5:
        return f"{symbol}{value / 1e5:.2f} L"
    return inr(value, symbol)


def sqft(value):
    if value is None:
        return "—"
    return f"{indian_group(value)} sq ft"


def km(value):
    if value is None:
        return "—"
    return f"{value:g} km"


def num(value):
    """Plain number for form inputs; blank for None/undefined (e.g. 6850000, 4.5)."""
    if value is None or value == "" or not isinstance(value, (int, float)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def yes_no(value):
    return "Yes" if value else "No"
