from __future__ import annotations


def naira(cents: int, currency: str = "NGN") -> str:
    sign = "-" if cents < 0 else ""
    value = abs(int(cents))
    major, minor = divmod(value, 100)
    grouped = f"{major:,}"
    if currency == "NGN":
        return f"{sign}₦{grouped}.{minor:02d}"
    return f"{sign}{currency} {grouped}.{minor:02d}"


def parse_amount(text: str) -> int:
    raw = (text or "").strip().replace("₦", "").replace(",", "").replace(" ", "")
    if not raw:
        return 0
    return int(round(float(raw) * 100))
