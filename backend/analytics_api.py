"""
Analytics API — Developer productivity trends with holiday highlighting.
Provides daily productivity % and work hours for line chart visualization.
Uses SQL aggregation + AFK ratio for speed, with daily caps for accuracy.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import Optional
from datetime import datetime, timedelta, timezone, date
from database import get_db
from models import Developer, Holiday
from afk_helpers import DAILY_TARGET_HOURS, MIN_WORKING_DAY_HOURS
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
        description="Filter: 3_months, current_month, last_month, current_fy, last_fy, ytd, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Custom end date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Developer analytics — daily productivity % using SQL aggregation with daily caps."""
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

        # SQL aggregation — daily totals (fast, single query)
        daily_rows = db.execute(text("""
            SELECT
                DATE(timestamp) AS day,
                SUM(CASE WHEN duration > 0 THEN duration ELSE 0 END) AS total_seconds,
                SUM(CASE WHEN duration > 0 AND LOWER(category) IN
                    ('development','database','productivity','browser','productive',
                     'server','system','other')
                    THEN duration ELSE 0 END) AS productive_seconds
            FROM activity_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
              AND duration > 0
            GROUP BY DATE(timestamp)
            ORDER BY day
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        # Daily AFK ratio (single query)
        afk_rows = db.execute(text("""
            SELECT
                DATE(timestamp) AS day,
                SUM(CASE WHEN status = 'not-afk' THEN duration ELSE 0 END) AS active_seconds,
                SUM(duration) AS total_afk_seconds
            FROM afk_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            GROUP BY DATE(timestamp)
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        # AFK ratio map: day → fraction of time user was active
        afk_ratio_map = {}
        for row in afk_rows:
            total_afk = row.total_afk_seconds or 0
            if total_afk > 0:
                afk_ratio_map[row.day] = (row.active_seconds or 0) / total_afk

        # Fetch holidays in range
        holidays = db.query(Holiday).filter(
            and_(Holiday.date >= start, Holiday.date <= end, Holiday.is_active == True)
        ).all()
        holiday_map = {}
        for h in holidays:
            h_date = h.date.date() if hasattr(h.date, 'date') and callable(h.date.date) else h.date
            holiday_map[h_date.isoformat()] = {"name": h.name, "type": h.holiday_type}

        # Index SQL results by date
        activity_by_day = {row.day: row for row in daily_rows}

        # Build daily analytics for ALL dates in range (fill gaps)
        daily_analytics = []
        total_work_hours = 0.0
        total_productive_hours = 0.0
        working_days = 0
        leave_days = 0

        start_date = start.date() if hasattr(start, 'date') else start
        end_date = end.date() if hasattr(end, 'date') else end
        current = start_date

        while current <= end_date:
            day_iso = current.isoformat()
            is_holiday = day_iso in holiday_map
            is_weekend = current.weekday() >= 5
            row = activity_by_day.get(current)

            if row:
                ratio = afk_ratio_map.get(current, 1.0)
                raw_total_h = (row.total_seconds * ratio) / 3600.0
                raw_prod_h = (row.productive_seconds * ratio) / 3600.0

                # Less than 2h activity on any day = not a real working day
                if raw_total_h <= MIN_WORKING_DAY_HOURS:
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
                    pct = (raw_prod_h / raw_total_h * 100) if raw_total_h > 0 else 0
                    pct = min(pct, 100.0)
                    total_h = min(raw_total_h, DAILY_TARGET_HOURS)
                    prod_h = min(raw_prod_h, DAILY_TARGET_HOURS)

                    entry = {
                        "date": day_iso,
                        "total_hours": round(total_h, 2),
                        "productive_hours": round(prod_h, 2),
                        "productivity_percentage": round(pct, 1),
                        "is_holiday": is_holiday,
                        "is_weekend": is_weekend,
                        "is_leave": False,
                        "status": "holiday" if is_holiday else "working",
                    }

                    if raw_total_h > MIN_WORKING_DAY_HOURS:
                        total_work_hours += total_h
                        total_productive_hours += prod_h
                        working_days += 1
            else:
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
