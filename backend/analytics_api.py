"""
Analytics API — Developer productivity trends with holiday highlighting.
Provides daily productivity % and work hours for line chart visualization.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import Optional
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from database import get_db
from models import Developer, Holiday
from afk_helpers import fetch_afk_data_single, compute_adjusted_duration, PRODUCTIVE_CATEGORIES
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/api/developer/{developer_id}/analytics")
async def get_developer_analytics(
    developer_id: str,
    period: str = Query("current_month",
        description="Filter: 3_months, current_month, last_month, current_fy, last_fy, ytd"),
    db: Session = Depends(get_db)
):
    """Developer analytics data for line chart — daily productivity % and work hours."""
    try:
        today = date.today()
        now = datetime.now(timezone.utc)

        # Resolve date range
        if period == "3_months":
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

        # Fetch activities
        activities = db.execute(text("""
            SELECT id, application_name, category, duration, timestamp, window_title
            FROM activity_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            ORDER BY timestamp ASC
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        # Fetch AFK data
        afk_data = fetch_afk_data_single(db, developer_id, start, end)

        # Compute daily stats with AFK adjustment
        daily_data = defaultdict(lambda: {"total": 0.0, "productive": 0.0, "count": 0})

        for row in activities:
            raw_dur = row.duration or 0
            if raw_dur <= 0:
                continue

            adj_dur = compute_adjusted_duration(
                row.timestamp, raw_dur, row.application_name,
                afk_data.not_afk_intervals, afk_data.all_afk_intervals
            )

            ts = row.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            day_key = ts.date()

            daily_data[day_key]["total"] += adj_dur
            daily_data[day_key]["count"] += 1
            cat = (row.category or "").lower()
            if cat in PRODUCTIVE_CATEGORIES:
                daily_data[day_key]["productive"] += adj_dur

        # Fetch holidays in range
        holidays = db.query(Holiday).filter(
            and_(
                Holiday.date >= start,
                Holiday.date <= end,
                Holiday.is_active == True
            )
        ).all()
        holiday_map = {}
        for h in holidays:
            h_date = h.date.date() if hasattr(h.date, 'date') and callable(h.date.date) else h.date
            holiday_map[h_date.isoformat()] = {"name": h.name, "type": h.holiday_type}

        # Build daily analytics array
        daily_analytics = []
        total_work_hours = 0.0
        total_productive_hours = 0.0
        working_days = 0

        for day_key in sorted(daily_data.keys()):
            d = daily_data[day_key]
            total_h = d["total"] / 3600.0
            prod_h = d["productive"] / 3600.0
            pct = (prod_h / total_h * 100) if total_h > 0 else 0
            is_holiday = day_key.isoformat() in holiday_map

            entry = {
                "date": day_key.isoformat(),
                "total_hours": round(total_h, 2),
                "productive_hours": round(prod_h, 2),
                "productivity_percentage": round(pct, 1),
                "is_holiday": is_holiday,
            }
            if is_holiday:
                entry["holiday_name"] = holiday_map[day_key.isoformat()]["name"]
                entry["holiday_type"] = holiday_map[day_key.isoformat()]["type"]

            daily_analytics.append(entry)

            if total_h > 2:  # Significant workdays only for averages
                total_work_hours += total_h
                total_productive_hours += prod_h
                working_days += 1

        avg_work_hours = round(total_work_hours / working_days, 2) if working_days > 0 else 0
        avg_productivity = round(
            (total_productive_hours / total_work_hours * 100) if total_work_hours > 0 else 0, 1
        )

        return {
            "developer": {"id": developer.developer_id, "name": developer.name},
            "period": period,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "summary": {
                "avg_work_hours": avg_work_hours,
                "avg_productivity_percentage": avg_productivity,
                "total_working_days": working_days,
                "total_work_hours": round(total_work_hours, 2),
                "total_productive_hours": round(total_productive_hours, 2)
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
