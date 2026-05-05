"""
Indian public holidays — used to exclude holiday dates from the 8-hour
productivity denominator.

On a holiday the developer is NOT expected to work, so the day should NOT
contribute the 8h floor to the denominator.  If a developer does work on a
holiday, their productive time is still counted in the numerator but the
denominator for that day is their actual tracked (not-AFK) time only.

Add new holidays as:  date(YYYY, M, D),  # Description
"""

from datetime import date

HOLIDAYS: frozenset = frozenset([

    # ── Fixed national / state holidays ──────────────────────────
    # Republic Day
    date(2025, 1, 26),
    date(2026, 1, 26),

    # Maharashtra Day / Labour Day
    date(2025, 5, 1),
    date(2026, 5, 1),

    # Independence Day
    date(2025, 8, 15),
    date(2026, 8, 15),

    # Gandhi Jayanti
    date(2025, 10, 2),
    date(2026, 10, 2),

    # Christmas
    date(2025, 12, 25),
    date(2026, 12, 25),

    # New Year
    date(2025, 1, 1),
    date(2026, 1, 1),
    date(2027, 1, 1),

    # ── 2025 floating holidays ────────────────────────────────────
    date(2025, 3, 14),   # Holi
    date(2025, 4, 18),   # Good Friday
    date(2025, 10, 20),  # Diwali / Laxmi Puja
    date(2025, 10, 21),  # Diwali (Bali Pratipada)

    # ── 2026 floating holidays ────────────────────────────────────
    date(2026, 3, 3),    # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 10, 21),  # Dussehra (approx)
    date(2026, 11, 8),   # Diwali / Laxmi Puja (approx)
    date(2026, 11, 9),   # Diwali (Bali Pratipada)

])


def is_holiday(d: date) -> bool:
    """Return True if the given date is a public holiday."""
    return d in HOLIDAYS
