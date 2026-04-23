"""
Cleanup API — Delete activity records captured during idle/AFK periods.

Retroactively removes activities that overlap with AFK time (when the developer
was not at the keyboard). This fixes historical data that was incorrectly
captured before the idle-pause feature was added to the agent.

Includes automatic daily cleanup via background scheduler.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
from database import get_db, SessionLocal
from afk_helpers import build_not_afk_intervals, build_all_afk_intervals, compute_active_duration
import asyncio
import logging

logger = logging.getLogger("cleanup_idle")

router = APIRouter()


# ============================================================
# BACKGROUND AUTO-CLEANUP (runs daily)
# ============================================================
def run_idle_cleanup_sync(days_back: int = 3) -> dict:
    """
    Standalone cleanup function (no FastAPI deps).
    Deletes idle activities for the last N days for all developers.
    Called by the background scheduler.
    """
    db = SessionLocal()
    try:
        start = (datetime.now(timezone.utc) - timedelta(days=days_back)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = datetime.now(timezone.utc)

        afk_rows = db.execute(text("""
            SELECT developer_id, status, duration, timestamp
            FROM afk_records
            WHERE timestamp >= :start_date AND timestamp <= :end_date
            ORDER BY developer_id, timestamp ASC
        """), {"start_date": start, "end_date": end}).fetchall()

        if not afk_rows:
            logger.info("Auto-cleanup: no AFK records found — skipping")
            return {"deleted": 0, "message": "no AFK records"}

        afk_by_dev = defaultdict(list)
        for row in afk_rows:
            afk_by_dev[row.developer_id].append(row)

        dev_intervals = {}
        for dev_id, dev_afk_rows in afk_by_dev.items():
            dev_intervals[dev_id] = {
                "not_afk": build_not_afk_intervals(dev_afk_rows),
                "all_afk": build_all_afk_intervals(dev_afk_rows),
            }

        activity_rows = db.execute(text("""
            SELECT id, developer_id, timestamp, duration
            FROM activity_records
            WHERE timestamp >= :start_date AND timestamp <= :end_date
            ORDER BY timestamp ASC
        """), {"start_date": start, "end_date": end}).fetchall()

        ids_to_delete = []
        for row in activity_rows:
            dev_id = row.developer_id
            if dev_id not in dev_intervals:
                continue
            if not dev_intervals[dev_id]["all_afk"]:
                continue

            act_start = row.timestamp
            if act_start.tzinfo is None:
                act_start = act_start.replace(tzinfo=timezone.utc)
            act_end = act_start + timedelta(seconds=row.duration or 0)

            active_seconds = compute_active_duration(
                act_start, act_end, dev_intervals[dev_id]["not_afk"]
            )
            if active_seconds <= 0:
                ids_to_delete.append(row.id)

        if ids_to_delete:
            for i in range(0, len(ids_to_delete), 500):
                batch = ids_to_delete[i:i + 500]
                db.execute(
                    text("DELETE FROM activity_records WHERE id = ANY(:ids)"),
                    {"ids": batch},
                )
            db.commit()

        result = {
            "deleted": len(ids_to_delete),
            "checked": len(activity_rows),
            "range": f"{start.date()} to {end.date()}",
        }
        logger.info(f"Auto-cleanup: deleted {len(ids_to_delete)} idle activities "
                     f"(checked {len(activity_rows)}, range {start.date()}-{end.date()})")
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Auto-cleanup error: {e}")
        return {"deleted": 0, "error": str(e)}
    finally:
        db.close()


async def daily_cleanup_loop():
    """Background loop: runs idle cleanup every 6 hours."""
    # Wait 60 seconds after startup before first run
    await asyncio.sleep(60)
    while True:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, run_idle_cleanup_sync, 3
            )
            logger.info(f"Scheduled cleanup result: {result}")
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
        # Run every 6 hours
        await asyncio.sleep(6 * 3600)


@router.post("/api/admin/cleanup-idle-activities")
async def cleanup_idle_activities(
    developer_id: Optional[str] = Query(None, description="Developer ID (None = all developers)"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD (None = all time)"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD (None = today)"),
    dry_run: bool = Query(True, description="True = preview only, False = actually delete"),
    db: Session = Depends(get_db),
):
    """
    Delete activity records that were captured during idle/AFK periods.

    How it works:
    1. Fetches all AFK records for the date range
    2. Builds "not-afk" intervals (when user was actually active)
    3. For each activity record, checks if it overlaps with any "not-afk" interval
    4. If activity has ZERO overlap with active time → delete it (idle capture)
    5. If activity partially overlaps → keep it (user was active for part of it)

    Use dry_run=true first to preview what would be deleted.
    """
    # Build date range
    if start_date:
        start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    else:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    if end_date:
        end = datetime.fromisoformat(end_date).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    else:
        end = datetime.now(timezone.utc)

    # Build developer filter
    dev_filter = ""
    params = {"start_date": start, "end_date": end}
    if developer_id:
        dev_filter = "AND developer_id = :dev_id"
        params["dev_id"] = developer_id

    # Fetch AFK records
    afk_rows = db.execute(text(f"""
        SELECT developer_id, status, duration, timestamp
        FROM afk_records
        WHERE timestamp >= :start_date AND timestamp <= :end_date
        {dev_filter}
        ORDER BY developer_id, timestamp ASC
    """), params).fetchall()

    if not afk_rows:
        return {
            "message": "No AFK records found for this range — cannot determine idle periods",
            "deleted": 0,
            "kept": 0,
        }

    # Group AFK data by developer
    afk_by_dev = defaultdict(list)
    for row in afk_rows:
        afk_by_dev[row.developer_id].append(row)

    # Build not-afk and all-afk intervals per developer
    dev_intervals = {}
    for dev_id, dev_afk_rows in afk_by_dev.items():
        dev_intervals[dev_id] = {
            "not_afk": build_not_afk_intervals(dev_afk_rows),
            "all_afk": build_all_afk_intervals(dev_afk_rows),
        }

    # Fetch activity records
    activity_rows = db.execute(text(f"""
        SELECT id, developer_id, timestamp, duration, application_name, window_title
        FROM activity_records
        WHERE timestamp >= :start_date AND timestamp <= :end_date
        {dev_filter}
        ORDER BY timestamp ASC
    """), params).fetchall()

    # Determine which activities to delete
    ids_to_delete = []
    kept_count = 0
    deleted_details = []

    for row in activity_rows:
        dev_id = row.developer_id
        if dev_id not in dev_intervals:
            # No AFK data for this developer — skip (can't determine idle)
            kept_count += 1
            continue

        not_afk = dev_intervals[dev_id]["not_afk"]
        all_afk = dev_intervals[dev_id]["all_afk"]

        if not all_afk:
            kept_count += 1
            continue

        act_start = row.timestamp
        if act_start.tzinfo is None:
            act_start = act_start.replace(tzinfo=timezone.utc)
        act_end = act_start + timedelta(seconds=row.duration or 0)

        # Check if activity has ANY overlap with not-afk (active) periods
        active_seconds = compute_active_duration(act_start, act_end, not_afk)

        if active_seconds <= 0:
            # Zero overlap with active time → this was captured during idle
            ids_to_delete.append(row.id)
            if len(deleted_details) < 50:  # Limit preview to 50 items
                deleted_details.append({
                    "developer": dev_id,
                    "timestamp": act_start.isoformat(),
                    "duration_sec": round(row.duration or 0, 1),
                    "app": row.application_name,
                    "title": (row.window_title or "")[:80],
                })
        else:
            kept_count += 1

    # Execute deletion if not dry run
    actually_deleted = 0
    if not dry_run and ids_to_delete:
        # Delete in batches of 500
        for i in range(0, len(ids_to_delete), 500):
            batch = ids_to_delete[i:i + 500]
            db.execute(
                text("DELETE FROM activity_records WHERE id = ANY(:ids)"),
                {"ids": batch},
            )
        db.commit()
        actually_deleted = len(ids_to_delete)

    return {
        "dry_run": dry_run,
        "date_range": f"{start.date()} to {end.date()}",
        "developer": developer_id or "all",
        "total_activities_checked": len(activity_rows),
        "to_delete": len(ids_to_delete),
        "kept": kept_count,
        "actually_deleted": actually_deleted,
        "message": (
            f"Preview: {len(ids_to_delete)} idle activities would be deleted"
            if dry_run
            else f"Deleted {actually_deleted} idle activities"
        ),
        "sample_deletions": deleted_details,
    }
