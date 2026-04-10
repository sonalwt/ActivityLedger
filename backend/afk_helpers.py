"""
Shared AFK-aware duration adjustment helpers.

ActivityWatch tracks raw window durations (time a window was open), but a user
may leave a tab open for hours without interacting.  These helpers use the
afk_records table (populated by the AFK watcher) to compute *active* duration
— the overlap between an activity window and the intervals where the user was
actually at the keyboard.

Key design: AFK data may be sparse.  We only apply AFK adjustment to activities
that have AFK *coverage* (i.e., there are afk or not-afk records overlapping
that activity's time window).  Activities with no AFK coverage use raw duration
(with a browser-cap fallback).
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict
from collections import defaultdict
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BROWSER_APPS = ['chrome', 'firefox', 'edge', 'safari', 'brave', 'opera']
MAX_SINGLE_EVENT_DURATION = 900  # 15-min fallback cap when no AFK coverage
PRODUCTIVE_CATEGORIES = ('coding', 'development', 'database', 'productivity', 'browser',
                         'productive', 'server', 'system', 'other')  # both old & new category names
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


def build_all_afk_intervals(afk_rows) -> List[Tuple[datetime, datetime]]:
    """Build sorted list of (start, end) for ALL afk records (both afk + not-afk).
    Used to determine which time periods have AFK watcher coverage."""
    intervals = []
    for row in afk_rows:
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


def _has_afk_coverage(activity_start, activity_end, all_afk_intervals) -> bool:
    """Check if there is ANY AFK watcher data covering this activity's time window."""
    for (afk_start, afk_end) in all_afk_intervals:
        if afk_end <= activity_start:
            continue
        if afk_start >= activity_end:
            break
        # There is overlap — AFK watcher was running during this activity
        return True
    return False


# ---------------------------------------------------------------------------
# Single-activity duration adjustment
# ---------------------------------------------------------------------------
def compute_adjusted_duration(timestamp, raw_duration, application_name,
                              not_afk_intervals, all_afk_intervals) -> float:
    """
    Return the AFK-adjusted duration for one activity event.

    - If AFK watcher covered this activity's time: return overlap with not-afk.
    - If no AFK coverage for this activity: use raw duration (browser cap fallback).
    """
    if raw_duration <= 0:
        return 0.0

    act_start = timestamp
    if act_start.tzinfo is None:
        act_start = act_start.replace(tzinfo=timezone.utc)
    act_end = act_start + timedelta(seconds=raw_duration)

    # Only apply AFK adjustment if the AFK watcher was running during this activity
    if all_afk_intervals and _has_afk_coverage(act_start, act_end, all_afk_intervals):
        active = compute_active_duration(act_start, act_end, not_afk_intervals)
        return min(active, raw_duration)

    # No AFK coverage — fallback: cap long browser events at 15 min
    if raw_duration > MAX_SINGLE_EVENT_DURATION:
        app_lower = (application_name or "").lower()
        if any(b in app_lower for b in BROWSER_APPS):
            return MAX_SINGLE_EVENT_DURATION

    return raw_duration


# ---------------------------------------------------------------------------
# AFK data container (holds both not-afk intervals and full coverage intervals)
# ---------------------------------------------------------------------------
class AFKData:
    """Holds both not-afk intervals and full AFK coverage for a developer."""
    __slots__ = ('not_afk_intervals', 'all_afk_intervals')

    def __init__(self, not_afk_intervals, all_afk_intervals):
        self.not_afk_intervals = not_afk_intervals
        self.all_afk_intervals = all_afk_intervals


# ---------------------------------------------------------------------------
# Bulk AFK fetch (one DB round-trip for all developers)
# ---------------------------------------------------------------------------
def fetch_afk_data_bulk(db, start, end) -> Dict[str, AFKData]:
    """
    Fetch AFK records for ALL developers in the date range.
    Returns dict mapping developer_id → AFKData(not_afk_intervals, all_afk_intervals).
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
        dev_id: AFKData(
            not_afk_intervals=build_not_afk_intervals(dev_rows),
            all_afk_intervals=build_all_afk_intervals(dev_rows),
        )
        for dev_id, dev_rows in grouped.items()
    }


# Keep old name for backward compatibility with activity_categorization_api
def fetch_afk_intervals_bulk(db, start, end) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """Fetch not-afk intervals for ALL developers (legacy wrapper)."""
    data = fetch_afk_data_bulk(db, start, end)
    return {dev_id: afk.not_afk_intervals for dev_id, afk in data.items()}


def fetch_afk_data_single(db, developer_id, start, end) -> AFKData:
    """Fetch AFK data for a single developer."""
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
    return AFKData(
        not_afk_intervals=build_not_afk_intervals(rows),
        all_afk_intervals=build_all_afk_intervals(rows),
    )


# Keep old name for backward compatibility
def fetch_afk_intervals_single(db, developer_id, start, end) -> List[Tuple[datetime, datetime]]:
    """Fetch not-afk intervals for a single developer (legacy wrapper)."""
    return fetch_afk_data_single(db, developer_id, start, end).not_afk_intervals


# ---------------------------------------------------------------------------
# Per-developer productivity computation (replaces SQL SUM(duration))
# ---------------------------------------------------------------------------
def compute_developer_productivity(activity_rows, afk_data,
                                   daily_target=DAILY_TARGET_HOURS):
    """
    Compute AFK-adjusted productivity totals for one developer.

    Parameters
    ----------
    activity_rows : list
        Raw rows from activity_records (need .category, .duration,
        .timestamp, .application_name).
    afk_data : AFKData or list
        AFKData instance, or a list of not-afk intervals (legacy).
    daily_target : float
        Max productive hours counted per day.

    Returns
    -------
    dict with keys: coding_hours, browser_hours, server_hours,
        productive_hours, total_hours, active_days
    """
    # Support both AFKData and legacy list format
    if isinstance(afk_data, AFKData):
        not_afk_intervals = afk_data.not_afk_intervals
        all_afk_intervals = afk_data.all_afk_intervals
    else:
        not_afk_intervals = afk_data
        all_afk_intervals = afk_data  # legacy: same list

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
            not_afk_intervals, all_afk_intervals
        )

        # Determine which day this activity belongs to
        ts = row.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        day_key = ts.date()

        daily[day_key]["total"] += adj_dur
        cat = (row.category or "").lower()
        if cat in ('coding', 'development', 'productivity', 'productive'):
            daily[day_key]["coding"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        elif cat == 'browser':
            daily[day_key]["browser"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        elif cat in ('database', 'server'):
            daily[day_key]["server"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        elif cat in ('system', 'other'):
            daily[day_key]["coding"] += adj_dur
            daily[day_key]["productive"] += adj_dur
        # entertainment, non-work → not productive

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
