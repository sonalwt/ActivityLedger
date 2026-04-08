"""
Shared AFK-aware duration adjustment helpers.

ActivityWatch tracks raw window durations (time a window was open), but a user
may leave a tab open for hours without interacting.  These helpers use the
afk_records table (populated by the AFK watcher) to compute *active* duration
— the overlap between an activity window and the intervals where the user was
actually at the keyboard.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict
from collections import defaultdict
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BROWSER_APPS = ['chrome', 'firefox', 'edge', 'safari', 'brave', 'opera']
MAX_SINGLE_EVENT_DURATION = 900  # 15-min fallback cap when no AFK data
PRODUCTIVE_CATEGORIES = ('development', 'database', 'productivity', 'browser')
DAILY_TARGET_HOURS = 8.0
MIN_WORKING_DAY_HOURS = 2.0  # Only count days with > 2h total activity


# ---------------------------------------------------------------------------
# Core AFK overlap functions (extracted from activity_categorization_api.py)
# ---------------------------------------------------------------------------
def build_not_afk_intervals(afk_rows) -> List[Tuple[datetime, datetime]]:
    """Build sorted list of (start, end) intervals where user was active."""
    intervals = []
    for row in afk_rows:
        if row.status == "not-afk":
            start = row.timestamp
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            end = start + timedelta(seconds=row.duration)
            intervals.append((start, end))
    intervals.sort(key=lambda x: x[0])
    return intervals


def compute_active_duration(
    activity_start: datetime,
    activity_end: datetime,
    not_afk_intervals: List[Tuple[datetime, datetime]]
) -> float:
    """Compute seconds of overlap between an activity and not-afk intervals."""
    total_active = 0.0
    for (naf_start, naf_end) in not_afk_intervals:
        if naf_end <= activity_start:
            continue
        if naf_start >= activity_end:
            break
        overlap_start = max(activity_start, naf_start)
        overlap_end = min(activity_end, naf_end)
        if overlap_start < overlap_end:
            total_active += (overlap_end - overlap_start).total_seconds()
    return total_active


# ---------------------------------------------------------------------------
# Single-activity duration adjustment
# ---------------------------------------------------------------------------
def compute_adjusted_duration(timestamp, raw_duration, application_name,
                              not_afk_intervals, has_afk_data) -> float:
    """
    Return the AFK-adjusted duration for one activity event.

    - If AFK data exists: return the overlap with not-afk intervals.
    - If no AFK data and it's a browser event > 15 min: cap at 15 min.
    - Otherwise: return raw duration unchanged.
    """
    if raw_duration <= 0:
        return 0.0

    if has_afk_data:
        act_start = timestamp
        if act_start.tzinfo is None:
            act_start = act_start.replace(tzinfo=timezone.utc)
        act_end = act_start + timedelta(seconds=raw_duration)
        active = compute_active_duration(act_start, act_end, not_afk_intervals)
        return min(active, raw_duration)

    # Fallback: cap long browser events when no AFK data available
    if raw_duration > MAX_SINGLE_EVENT_DURATION:
        app_lower = (application_name or "").lower()
        if any(b in app_lower for b in BROWSER_APPS):
            return MAX_SINGLE_EVENT_DURATION

    return raw_duration


# ---------------------------------------------------------------------------
# Bulk AFK fetch (one DB round-trip for all developers)
# ---------------------------------------------------------------------------
def fetch_afk_intervals_bulk(db, start, end) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """
    Fetch AFK records for ALL developers in the date range.
    Returns dict mapping developer_id → sorted list of not-afk intervals.
    """
    afk_query = text("""
        SELECT developer_id, status, duration, timestamp
        FROM afk_records
        WHERE timestamp >= :start_date
          AND timestamp <= :end_date
        ORDER BY developer_id, timestamp ASC
    """)
    rows = db.execute(afk_query, {"start_date": start, "end_date": end}).fetchall()

    grouped: Dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row.developer_id].append(row)

    return {
        dev_id: build_not_afk_intervals(dev_rows)
        for dev_id, dev_rows in grouped.items()
    }


def fetch_afk_intervals_single(db, developer_id, start, end) -> List[Tuple[datetime, datetime]]:
    """Fetch AFK intervals for a single developer."""
    afk_query = text("""
        SELECT status, duration, timestamp
        FROM afk_records
        WHERE developer_id = :dev_id
          AND timestamp >= :start_date
          AND timestamp <= :end_date
        ORDER BY timestamp ASC
    """)
    rows = db.execute(afk_query, {
        "dev_id": developer_id,
        "start_date": start,
        "end_date": end
    }).fetchall()
    return build_not_afk_intervals(rows)


# ---------------------------------------------------------------------------
# Per-developer productivity computation (replaces SQL SUM(duration))
# ---------------------------------------------------------------------------
def compute_developer_productivity(activity_rows, not_afk_intervals,
                                   daily_target=DAILY_TARGET_HOURS):
    """
    Compute AFK-adjusted productivity totals for one developer.

    Parameters
    ----------
    activity_rows : list
        Raw rows from activity_records (need .category, .duration,
        .timestamp, .application_name).
    not_afk_intervals : list of (start, end) tuples
        Active intervals for this developer. Empty list = no AFK data.
    daily_target : float
        Max productive hours counted per day.

    Returns
    -------
    dict with keys: coding_hours, browser_hours, server_hours,
        productive_hours, total_hours, active_days
    """
    has_afk = len(not_afk_intervals) > 0

    # Accumulate per-day stats
    daily = defaultdict(lambda: {
        "total": 0.0, "coding": 0.0, "browser": 0.0,
        "server": 0.0, "productive": 0.0
    })

    for row in activity_rows:
        raw_dur = row.duration or 0
        if raw_dur <= 0:
            continue

        adj_dur = compute_adjusted_duration(
            row.timestamp, raw_dur, row.application_name,
            not_afk_intervals, has_afk
        )

        # Determine which day this activity belongs to
        ts = row.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        day_key = ts.date()

        daily[day_key]["total"] += adj_dur
        cat = (row.category or "").lower()
        if cat in ('development', 'productivity'):
            daily[day_key]["coding"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        elif cat == 'browser':
            daily[day_key]["browser"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        elif cat == 'database':
            daily[day_key]["server"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        # entertainment, system, other, non-work → not productive

    # Aggregate across days (only days with > MIN_WORKING_DAY_HOURS)
    total_coding = 0.0
    total_browser = 0.0
    total_server = 0.0
    total_productive = 0.0  # capped per day
    total_hours = 0.0
    active_days = 0

    for day_key, stats in daily.items():
        day_total_h = stats["total"] / 3600.0
        if day_total_h <= MIN_WORKING_DAY_HOURS:
            continue

        active_days += 1
        total_hours += day_total_h
        total_coding += stats["coding"] / 3600.0
        total_browser += stats["browser"] / 3600.0
        total_server += stats["server"] / 3600.0
        # Cap productive hours at daily target
        day_productive_h = min(stats["productive"] / 3600.0, daily_target)
        total_productive += day_productive_h

    return {
        "coding_hours": total_coding,
        "browser_hours": total_browser,
        "server_hours": total_server,
        "productive_hours": total_productive,
        "total_hours": total_hours,
        "active_days": active_days,
    }
