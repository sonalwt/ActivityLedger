"""
Analytics API — Developer productivity trends with holiday highlighting.
Provides daily productivity % and work hours for line chart visualization.
Uses the SAME categorization + AFK logic as the Developer Dashboard for consistency.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from database import get_db
from models import Developer, Holiday
from activity_categorizer import get_categorizer
from afk_helpers import (
    DAILY_TARGET_HOURS, MIN_WORKING_DAY_HOURS,
    build_not_afk_intervals, compute_active_duration,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Constants — must match activity_categorization_api.py exactly
# ---------------------------------------------------------------------------
_SKIP_TITLES = frozenset([
    'untitled', 'program manager', 'task switching',
    'task view', 'windows default lock screen', 'new tab', 'blank',
])
_SYSTEM_TITLES = frozenset(['search', 'task manager', 'control panel'])
_BROWSER_APPS = ('chrome', 'firefox', 'edge', 'safari', 'brave', 'opera')
_EMAIL_KEYWORDS = (
    "mail", "inbox", "compose", "@gmail", "@outlook",
    "@yahoo", "@hotmail", "webmail", "thunderbird",
)
_DOC_KEYWORDS = (
    "google docs", "google sheets", "google slides",
    "spreadsheet", "presentation", ".pdf", ".docx",
    ".xlsx", ".pptx", "word online", "excel online",
    "onedrive", "sharepoint",
)
_PRODUCTIVE_CATS = frozenset(["coding", "browser", "server"])


def _get_indian_financial_year_range(fy_offset: int = 0):
    """
    Returns (start_date, end_date) for Indian Financial Year (April 1 – March 31).
    fy_offset=0 → current FY, fy_offset=-1 → last FY.
    """
    today = date.today()
    fy_start_year = today.year if today.month >= 4 else today.year - 1
    fy_start_year += fy_offset
    start = datetime(fy_start_year, 4, 1, tzinfo=timezone.utc)
    end = datetime(fy_start_year + 1, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _build_daily_afk_map(not_afk_intervals):
    """Pre-split AFK intervals by day for O(1) day-lookup instead of full scan."""
    daily = defaultdict(list)
    for start, end in not_afk_intervals:
        day = start.date()
        daily[day].append((start, end))
        end_day = end.date()
        if end_day != day:
            daily[end_day].append((start, end))
    return daily


def _compute_all_days(rows, categorizer, not_afk_intervals, has_afk_data):
    """
    Single-pass batch processor — same logic as Dashboard but optimized for
    365-day ranges with category caching and per-day AFK intervals.

    Returns dict[date] → (tracked_total_sec, productive_sec).
    """
    # Pre-split AFK intervals by day (avoids scanning full-year list per activity)
    daily_afk = _build_daily_afk_map(not_afk_intervals) if has_afk_data else {}

    # Category cache — same (title, app, project) combo categorized once
    cat_cache = {}
    _VALID_CATS = frozenset(("coding", "browser", "server", "non-work"))

    # Per-day accumulators
    day_tracked = defaultdict(float)
    # Dedup: day → {(cat, title_lower): {"dur": float, "app_lower": str}}
    day_dedup = defaultdict(dict)

    for row in rows:
        window_title = row.window_title or ""
        if not window_title.strip() and row.file_path:
            fp = row.file_path
            window_title = (
                fp.rsplit('/', 1)[-1] if '/' in fp
                else fp.rsplit('\\', 1)[-1] if '\\' in fp
                else fp
            )

        title_lower = window_title.strip().lower()
        if title_lower in _SKIP_TITLES:
            continue

        raw_duration = row.duration or 0
        if raw_duration <= 0:
            continue

        if title_lower in _SYSTEM_TITLES and raw_duration > 60:
            raw_duration = 60

        day = row.timestamp.date()

        # Per-activity AFK adjustment using day-specific intervals
        if has_afk_data and raw_duration > 0:
            activity_ts = row.timestamp
            if activity_ts.tzinfo is None:
                activity_ts = activity_ts.replace(tzinfo=timezone.utc)
            day_intervals = daily_afk.get(day)
            if day_intervals:
                active_seconds = compute_active_duration(
                    activity_ts,
                    activity_ts + timedelta(seconds=raw_duration),
                    day_intervals,
                )
                raw_duration = min(active_seconds, raw_duration)
        elif not has_afk_data and raw_duration > 900:
            app_lower = (row.application_name or "").lower()
            if any(b in app_lower for b in _BROWSER_APPS):
                raw_duration = 900

        # Categorize with cache (biggest speedup — avoids re-categorizing
        # the same "Gmail - Inbox" title thousands of times across the year)
        app_name = row.application_name or ""
        project_name = row.project_name or ""
        cache_key = (title_lower, app_name.lower(), project_name.lower())
        cat = cat_cache.get(cache_key)
        if cat is None:
            cat, _ = categorizer.categorize_activity(window_title, app_name, project_name)
            if cat not in _VALID_CATS:
                cat = "browser"
            cat_cache[cache_key] = cat

        day_tracked[day] += raw_duration

        # Accumulate into dedup structure (numeric only, no dict-of-dicts)
        dedup_key = (cat, title_lower)
        entry = day_dedup[day].get(dedup_key)
        if entry is None:
            day_dedup[day][dedup_key] = {"dur": raw_duration, "app_lower": app_name.lower()}
        else:
            entry["dur"] += raw_duration

    # Calculate productive seconds per day (after dedup + caps)
    result = {}
    for day, entries in day_dedup.items():
        productive = 0.0
        for (cat, title_lower), info in entries.items():
            dur = info["dur"]
            # Apply email/doc caps when no AFK data
            if not has_afk_data:
                if any(b in info["app_lower"] for b in _BROWSER_APPS):
                    if any(kw in title_lower for kw in _EMAIL_KEYWORDS):
                        dur = min(dur, 600)
                    elif any(kw in title_lower for kw in _DOC_KEYWORDS):
                        dur = min(dur, 900)
            if cat in _PRODUCTIVE_CATS:
                productive += dur
        result[day] = (day_tracked[day], productive)

    return result


@router.get("/api/developer/{developer_id}/analytics")
async def get_developer_analytics(
    developer_id: str,
    period: str = Query("current_month",
        description="Filter: 3_months, current_month, last_month, current_fy, last_fy, ytd, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Custom end date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Developer analytics — daily productivity % matching the Developer Dashboard."""
    try:
        today = date.today()
        now = datetime.now(timezone.utc)

        # Resolve date range
        if period == "custom" and start_date and end_date:
            start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        elif period == "3_months":
            start = datetime(today.year, today.month, 1, tzinfo=timezone.utc) - timedelta(days=90)
            start = start.replace(day=1, hour=0, minute=0, second=0)
            end = now
        elif period == "last_month":
            first_of_this_month = date(today.year, today.month, 1)
            last_month_end = first_of_this_month - timedelta(days=1)
            start = datetime(last_month_end.year, last_month_end.month, 1, tzinfo=timezone.utc)
            end = datetime(last_month_end.year, last_month_end.month, last_month_end.day,
                          23, 59, 59, tzinfo=timezone.utc)
        elif period == "current_fy":
            start, end = _get_indian_financial_year_range(0)
            if end > now:
                end = now
        elif period == "last_fy":
            start, end = _get_indian_financial_year_range(-1)
        elif period == "ytd":
            start = datetime(today.year, 1, 1, tzinfo=timezone.utc)
            end = now
        else:  # current_month (default)
            start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
            end = now

        # Verify developer exists
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")

        # ----- Fetch raw activities (same query as dashboard) -----
        rows = db.execute(text("""
            SELECT id, application_name, window_title, duration, timestamp,
                   url, file_path, project_name
            FROM activity_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
              AND LOWER(COALESCE(application_name, '')) NOT IN ('unknown', '')
            ORDER BY timestamp ASC
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        # ----- Fetch AFK records (same as dashboard) -----
        afk_rows = db.execute(text("""
            SELECT status, duration, timestamp
            FROM afk_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            ORDER BY timestamp ASC
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        not_afk_intervals = build_not_afk_intervals(afk_rows)
        has_afk_data = len(not_afk_intervals) > 0

        categorizer = get_categorizer()

        # Single-pass batch computation (cached + per-day AFK)
        daily_productivity = _compute_all_days(
            rows, categorizer, not_afk_intervals, has_afk_data
        )

        # ----- Fetch holidays -----
        holidays = db.query(Holiday).filter(
            and_(Holiday.date >= start, Holiday.date <= end, Holiday.is_active == True)
        ).all()
        holiday_map = {}
        for h in holidays:
            h_date = h.date.date() if hasattr(h.date, 'date') and callable(h.date.date) else h.date
            holiday_map[h_date.isoformat()] = {"name": h.name, "type": h.holiday_type}

        # ----- Build daily analytics -----
        daily_analytics = []
        total_work_hours = 0.0
        total_productive_hours = 0.0
        working_days = 0
        leave_days = 0

        range_start = start.date() if hasattr(start, 'date') else start
        range_end = end.date() if hasattr(end, 'date') else end
        current = range_start

        while current <= range_end:
            day_iso = current.isoformat()
            is_holiday = day_iso in holiday_map
            is_weekend = current.weekday() >= 5
            day_data = daily_productivity.get(current)

            if day_data:
                tracked_sec, productive_sec = day_data
                total_h = tracked_sec / 3600.0

                if total_h <= MIN_WORKING_DAY_HOURS:
                    # Not enough activity to count as a working day
                    if is_holiday:
                        status = "holiday"
                    elif is_weekend:
                        status = "weekend"
                    else:
                        status = "leave"
                        leave_days += 1
                    entry = {
                        "date": day_iso,
                        "total_hours": 0,
                        "productive_hours": 0,
                        "productivity_percentage": 0,
                        "is_holiday": is_holiday,
                        "is_weekend": is_weekend,
                        "is_leave": status == "leave",
                        "status": status,
                    }
                else:
                    # Use 8h daily target as denominator (not just tracked time)
                    target_sec = DAILY_TARGET_HOURS * 3600
                    pct = min(100.0, (productive_sec / target_sec * 100)) if target_sec > 0 else 0
                    prod_h = productive_sec / 3600.0
                    display_total_h = min(total_h, DAILY_TARGET_HOURS)
                    display_prod_h = min(prod_h, DAILY_TARGET_HOURS)

                    entry = {
                        "date": day_iso,
                        "total_hours": round(display_total_h, 2),
                        "productive_hours": round(display_prod_h, 2),
                        "productivity_percentage": round(pct, 1),
                        "is_holiday": is_holiday,
                        "is_weekend": is_weekend,
                        "is_leave": False,
                        "status": "holiday" if is_holiday else "working",
                    }
                    total_work_hours += display_total_h
                    total_productive_hours += display_prod_h
                    working_days += 1
            else:
                # No activity at all
                if is_holiday:
                    status = "holiday"
                elif is_weekend:
                    status = "weekend"
                else:
                    status = "leave"
                    leave_days += 1

                entry = {
                    "date": day_iso,
                    "total_hours": 0,
                    "productive_hours": 0,
                    "productivity_percentage": 0,
                    "is_holiday": is_holiday,
                    "is_weekend": is_weekend,
                    "is_leave": status == "leave",
                    "status": status,
                }

            if is_holiday:
                entry["holiday_name"] = holiday_map[day_iso]["name"]
                entry["holiday_type"] = holiday_map[day_iso]["type"]

            daily_analytics.append(entry)
            current += timedelta(days=1)

        avg_work_hours = round(total_work_hours / working_days, 2) if working_days > 0 else 0
        avg_productivity = round(
            (total_productive_hours / total_work_hours * 100) if total_work_hours > 0 else 0, 1
        )
        avg_productivity = min(avg_productivity, 100.0)

        return {
            "developer": {"id": developer.developer_id, "name": developer.name},
            "period": period,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "summary": {
                "avg_work_hours": avg_work_hours,
                "avg_productivity_percentage": avg_productivity,
                "total_working_days": working_days,
                "total_work_hours": round(total_work_hours, 2),
                "total_productive_hours": round(total_productive_hours, 2),
                "leave_days": leave_days
            },
            "daily_analytics": daily_analytics,
            "holidays_in_range": list(holiday_map.values())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in developer analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Holiday CRUD ---

@router.get("/api/holidays")
async def get_holidays(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all holidays, optionally filtered by date range."""
    try:
        query = db.query(Holiday).filter(Holiday.is_active == True)
        if start_date:
            query = query.filter(Holiday.date >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
        if end_date:
            query = query.filter(Holiday.date <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))

        holidays = query.order_by(Holiday.date).all()
        return {
            "holidays": [
                {"id": h.id, "date": h.date.isoformat(), "name": h.name, "holiday_type": h.holiday_type}
                for h in holidays
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching holidays: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/holidays")
async def create_holiday(
    date: str = Query(...),
    name: str = Query(...),
    holiday_type: str = Query("national"),
    db: Session = Depends(get_db)
):
    """Create a new holiday entry."""
    try:
        holiday_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        new_holiday = Holiday(date=holiday_date, name=name, holiday_type=holiday_type)
        db.add(new_holiday)
        db.commit()
        db.refresh(new_holiday)
        return {
            "success": True,
            "holiday": {"id": new_holiday.id, "date": new_holiday.date.isoformat(),
                        "name": new_holiday.name, "holiday_type": new_holiday.holiday_type}
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating holiday: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/holidays/seed-indian")
async def seed_indian_holidays(
    year: int = Query(default=2026, description="Year to seed holidays for"),
    db: Session = Depends(get_db)
):
    """Seed standard Indian national holidays for a given year."""
    try:
        indian_holidays = [
            (f"{year}-01-26", "Republic Day", "national"),
            (f"{year}-03-14", "Holi", "national"),
            (f"{year}-03-31", "Id-ul-Fitr", "national"),
            (f"{year}-04-06", "Ram Navami", "national"),
            (f"{year}-04-10", "Mahavir Jayanti", "national"),
            (f"{year}-04-14", "Dr. Ambedkar Jayanti", "national"),
            (f"{year}-04-18", "Good Friday", "national"),
            (f"{year}-05-01", "May Day", "optional"),
            (f"{year}-05-12", "Buddha Purnima", "national"),
            (f"{year}-06-07", "Eid-ul-Adha", "national"),
            (f"{year}-07-06", "Muharram", "national"),
            (f"{year}-08-15", "Independence Day", "national"),
            (f"{year}-08-16", "Janmashtami", "national"),
            (f"{year}-09-05", "Milad-un-Nabi", "national"),
            (f"{year}-10-02", "Mahatma Gandhi Jayanti", "national"),
            (f"{year}-10-02", "Dussehra", "national"),
            (f"{year}-10-20", "Diwali", "national"),
            (f"{year}-10-21", "Diwali (Day 2)", "national"),
            (f"{year}-11-05", "Guru Nanak Jayanti", "national"),
            (f"{year}-12-25", "Christmas Day", "national"),
        ]

        created = 0
        for date_str, name, h_type in indian_holidays:
            dt = datetime.fromisoformat(date_str + "T00:00:00+00:00")
            existing = db.query(Holiday).filter(
                and_(Holiday.date == dt, Holiday.name == name)
            ).first()
            if not existing:
                db.add(Holiday(date=dt, name=name, holiday_type=h_type))
                created += 1

        db.commit()
        return {"success": True, "created": created, "year": year}
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding holidays: {e}")
        raise HTTPException(status_code=500, detail=str(e))
