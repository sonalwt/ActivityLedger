import sys, os, json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import your analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.activity_analyzer import ActivityAnalyzer

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'timesheet',
    'user': 'postgres',
    'password': 'asdf1234'
}

engine = create_engine(f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
SessionLocal = sessionmaker(bind=engine)

# Initialize analyzer
analyzer = ActivityAnalyzer(DB_CONFIG)

# --- Categorize activity ---
def categorize_activity(activity: dict) -> str:
    app_name = (activity.get("app") or "").lower()
    title = (activity.get("title") or "").lower()

    productivity_apps = ["code.exe", "cpanel", "shareplex", "filezilla"]
    server_keywords = ["aws", "google", "gcp", "termius", "azure"]
    browser_keywords = ["youtube", "gmail", "research", "stackoverflow", "github"]

    if any(k in app_name for k in productivity_apps):
        return "productivity"
    if "chrome.exe" in app_name and any(k in title for k in server_keywords):
        return "server"
    if any(k in title for k in browser_keywords):
        return "browser"
    return "other"

# --- API: Get activity data ---
@app.get("/api/activity-data/{developer_id}")
def get_activity_data(
    developer_id: str,
    start_date: str = Query(..., description="Start date in ISO format"),
    end_date: str = Query(..., description="End date in ISO format")
):
    try:
        start = datetime.fromisoformat(start_date.replace("Z", ""))
        end = datetime.fromisoformat(end_date.replace("Z", ""))

        query = text("""
            SELECT activity_data, created_at
            FROM activity_records
            WHERE developer_id = :dev
              AND created_at BETWEEN :start AND :end
            ORDER BY created_at ASC
        """)

        session = SessionLocal()
        result = session.execute(query, {"dev": developer_id, "start": start, "end": end}).fetchall()
        session.close()

        all_activities = []
        total_time_seconds = 0
        category_breakdown = {
            "productivity": 0, "server": 0, "browser": 0, "non-work": 0, "uncategorized": 0
        }

        for row in result:
            activities = row["activity_data"]
            if isinstance(activities, str):
                activities = json.loads(activities)
            for act in activities:
                category = categorize_activity(act)
                category_breakdown[category] += act.get("duration", 0)
                total_time_seconds += act.get("duration", 0)
                all_activities.append({
                    "timestamp": row["created_at"].isoformat(),
                    "app": act.get("app"),
                    "title": act.get("title"),
                    "duration": act.get("duration", 0),
                    "category": category
                })

        total_hours = sum(category_breakdown.values())
        for cat in category_breakdown:
            category_breakdown[cat] = {
                "hours": round(category_breakdown[cat]/3600, 2),
                "percentage": round((category_breakdown[cat]/total_hours)*100,1) if total_hours>0 else 0
            }

        return {
            "data": all_activities,
            "total_time": total_time_seconds,
            "category_breakdown": category_breakdown
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- API: Get all developers ---
@app.get("/api/developers")
def get_developers():
    try:
        query = text("""
            SELECT DISTINCT developer_id
            FROM activity_records
            WHERE developer_id IS NOT NULL AND developer_id != ''
            ORDER BY developer_id
        """)
        session = SessionLocal()
        result = session.execute(query).fetchall()
        session.close()

        developers = [{"id": row[0], "name": f"Developer {row[0]}"} for row in result]
        return developers

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- API: Weekly productivity ---
@app.get("/api/productivity/{developer_id}/weekly")
def get_weekly_productivity(developer_id: str):
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)

        dates, scores = [], []
        current = start_date
        while current <= end_date:
            activities, total_duration = analyzer.get_developer_activities(
                developer_id, current, current
            )
            score = analyzer.calculate_productivity_score(activities, total_duration)
            dates.append(current.strftime('%a'))
            scores.append(score)
            current += timedelta(days=1)

        return {"dates": dates, "scores": scores}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard_api:app", host="0.0.0.0", port=8000, reload=True)
