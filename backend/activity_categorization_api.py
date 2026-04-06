# activity_categorization_api.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from database import get_db
from activity_categorizer import get_categorizer
import json

router = APIRouter()

# Use raw timestamp - frontend already sends IST-adjusted dates
TIMEZONE_CORRECTED_TIMESTAMP = "timestamp"


# ============================================================
# ACTUAL WORK HOURS CALCULATION
# ============================================================
def calculate_actual_work_hours(db_rows):
    if not db_rows:
        return 0, {}
    
    daily = {}
    for row in db_rows:
        d = row.timestamp.date()

        if d not in daily:
            daily[d] = []

        daily[d].append({
            "timestamp": row.timestamp,
            "duration": row.duration or 0,
            "application_name": row.application_name,
            "window_title": row.window_title
        })

    total = 0
    daily_output = {}

    for d, acts in daily.items():
        # Rows already sorted by timestamp ASC from SQL query
        first_time = acts[0]["timestamp"]
        last = acts[-1]
        last_time = last["timestamp"] + timedelta(seconds=last["duration"])

        seconds = min((last_time - first_time).total_seconds(), 16*3600)

        unique_apps = len(set(a["application_name"] for a in acts if a["application_name"]))

        daily_output[str(d)] = {
            "start_time": first_time.isoformat(),
            "end_time": last_time.isoformat(),
            "duration_seconds": seconds,
            "duration_hours": round(seconds/3600, 2),
            "activity_count": len(acts),
            "unique_applications": unique_apps
        }

        total += seconds

    return total, daily_output



# ============================================================
# HELPER — FORMAT DURATION
# ============================================================
def format_duration(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{round(seconds/3600,1)}h"
    elif seconds >= 60:
        return f"{round(seconds/60,1)}m"
    return f"{seconds}s"



# ============================================================
# AFK-AWARE DURATION ADJUSTMENT
# ============================================================
def build_not_afk_intervals(afk_rows) -> List[Tuple[datetime, datetime]]:
    """Build sorted list of (start, end) intervals where user was active (not-afk)."""
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


# ============================================================
# MAIN API — FIXED WITH DEDUP + CORRECT DURATIONS
# ============================================================
@router.get("/api/activity-categories/{developer_id}")
async def get_categorized_activities(
    developer_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        categorizer = get_categorizer()

        start = (
            datetime.fromisoformat(start_date.replace("Z","+00:00"))
            if start_date else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        end = (
            datetime.fromisoformat(end_date.replace("Z","+00:00"))
            if end_date else datetime.now(timezone.utc)
        )

        # ---------------------------------------------------
        # Get rows from DB
        # ---------------------------------------------------
        query = text(f"""
            SELECT
                id, developer_id, application_name, window_title,
                duration, timestamp, url, file_path, project_name,
                project_type, category
            FROM activity_records
            WHERE developer_id = :dev_id
              AND ({TIMEZONE_CORRECTED_TIMESTAMP}) >= :start_date
              AND ({TIMEZONE_CORRECTED_TIMESTAMP}) <= :end_date
              AND LOWER(COALESCE(application_name, '')) NOT IN ('unknown', '')
            ORDER BY timestamp ASC
        """)

        rows = db.execute(query, {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()

        # ---------------------------------------------------
        # Fetch AFK records for idle-time adjustment
        # ---------------------------------------------------
        afk_query = text("""
            SELECT status, duration, timestamp
            FROM afk_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            ORDER BY timestamp ASC
        """)
        afk_rows = db.execute(afk_query, {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()

        not_afk_intervals = build_not_afk_intervals(afk_rows)
        has_afk_data = len(not_afk_intervals) > 0

        # ---------------------------------------------------
        # Calculate ACTUAL work hours
        # ---------------------------------------------------
        actual_work_seconds, daily_breakdown = calculate_actual_work_hours(rows)

        categories = ["productive", "browser", "server", "non-work"]

        # Store raw activity rows grouped by category
        cat_raw = {c: [] for c in categories}
        tracked_total_sec = 0

        for row in rows:
            window_title = row.window_title or ""

            # Derive window_title from file_path when empty (fixes VS Code watcher data)
            if not window_title.strip() and row.file_path:
                fp = row.file_path
                window_title = fp.rsplit('/', 1)[-1] if '/' in fp else fp.rsplit('\\', 1)[-1] if '\\' in fp else fp

            # Skip meaningless entries - don't include in any calculations
            skip_titles = ['untitled', 'program manager', 'task switching',
                           'task view', 'windows default lock screen', 'new tab', 'blank']
            if window_title.strip().lower() in skip_titles:
                continue

            # Cap duration for system/non-work window titles (max 60 seconds each)
            system_titles = ['search', 'task manager', 'control panel']
            raw_duration = row.duration or 0
            if window_title.strip().lower() in system_titles and raw_duration > 60:
                raw_duration = 60

            # Adjust duration using AFK data — only count time user was active
            if has_afk_data and raw_duration > 0:
                activity_ts = row.timestamp
                if activity_ts.tzinfo is None:
                    activity_ts = activity_ts.replace(tzinfo=timezone.utc)
                active_seconds = compute_active_duration(
                    activity_ts,
                    activity_ts + timedelta(seconds=raw_duration),
                    not_afk_intervals
                )
                raw_duration = min(active_seconds, raw_duration)
            elif not has_afk_data and raw_duration > 900:
                # Fallback for historical data (no AFK records):
                # Cap browser/mail events at 15 min per single event.
                # Long single events mean the user was likely idle.
                app_lower = (row.application_name or "").lower()
                is_browser = any(b in app_lower for b in ['chrome', 'firefox', 'edge', 'safari', 'brave', 'opera'])
                if is_browser:
                    raw_duration = 900  # 15 minutes max per browser event

            act = {
                "id": row.id,
                "application_name": row.application_name or "",
                "window_title": window_title,
                "duration": raw_duration,
                "timestamp": row.timestamp.isoformat(),
                "project_name": row.project_name,
                "project_type": row.project_type,
                "url": row.url,
                "file_path": row.file_path,
            }

            ci = categorizer.get_detailed_category(act["window_title"], act["application_name"], act.get("project_name") or "")
            cat = ci["category"]
            if cat not in categories:
                cat = "browser"

            cat_raw[cat].append(act)
            tracked_total_sec += act["duration"]

        # ============================================================
        # FIXED: DEDUPLICATE ACTIVITIES
        # ============================================================
        grouped_output = {}

        for cat, acts in cat_raw.items():
            dedup = {}

            for a in acts:
                key = a["window_title"].strip().lower()

                if key not in dedup:
                    dedup[key] = {
                        **a,
                        "duration": 0,
                        "activity_count": 0
                    }

                dedup[key]["duration"] += a["duration"]
                dedup[key]["activity_count"] += 1

            # Convert to list
            merged_list = list(dedup.values())

            # Apply formatting
            for item in merged_list:
                d = item["duration"]
                item["duration_hours"] = round(d/3600, 3)
                item["duration_display"] = format_duration(d)

            # Sort by longest duration
            grouped_output[cat] = sorted(merged_list, key=lambda x: x["duration"], reverse=True)



        # ============================================================
        # CATEGORY STATS
        # ============================================================
        cat_stats = {c: {"count": 0, "duration": 0} for c in categories}

        for cat, acts in grouped_output.items():
            for a in acts:
                cat_stats[cat]["count"] += 1
                cat_stats[cat]["duration"] += a["duration"]

        for cat in categories:
            dur = cat_stats[cat]["duration"]
            cat_stats[cat]["duration_hours"] = round(dur/3600, 3)
            cat_stats[cat]["percentage"] = (
                round((dur / tracked_total_sec) * 100, 2) if tracked_total_sec > 0 else 0
            )



        # ============================================================
        # TOP ACTIVITIES PER CATEGORY (deduped)
        # ============================================================
        top_activities_by_category = {}

        for cat, acts in grouped_output.items():
            top_activities_by_category[cat] = [
                {
                    **a,
                    "duration": a["duration"],
                    "duration_display": format_duration(a["duration"]),
                    "duration_hours": round(a["duration"]/3600, 3)
                }
                for a in acts[:10]
            ]


        # ============================================================
        # Return Response
        # ============================================================
        return {
            "developer_id": developer_id,

            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days": len(daily_breakdown)
            },

            "actual_work_seconds": actual_work_seconds,
            "actual_work_hours": round(actual_work_seconds/3600, 2),

            "daily_work_breakdown": daily_breakdown,

            "total_tracked_seconds": tracked_total_sec,
            "total_tracked_hours": round(tracked_total_sec/3600, 2),

            "statistics": cat_stats,

            "activities_by_category": grouped_output,
            "top_activities_by_category": top_activities_by_category
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
