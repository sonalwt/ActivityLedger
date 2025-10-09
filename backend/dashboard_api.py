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
    app_name = (activity.get("application_name") or "").lower()
    title = (activity.get("window_title") or "").lower()
    urls = [url.lower() for url in activity.get("urls") or []]

    if any(x in title for x in ["lock", "locked"]) or any(x in app_name for x in ["lockapp", "logonui"]):
        return "non-work"
    if any(x in title for x in ["youtube", "netflix", "spotify", "music"]):
        return "non-work"

    productivity_apps = ["vscode", "code.exe", "pycharm", "intellij", "sublime", "atom", "notepad++", "vim", "emacs", "notion", "jira", "trello", "figma", "photoshop"]
    if any(x in app_name for x in productivity_apps):
        return "productivity"

    server_keywords = ["aws", "azure", "gcp", "plesk", "cpanel", "whm", "directadmin", "webmin", "ssh", "putty", "filezilla", "localhost", "127.0.0.1", "digitalocean", "linode"]
    if any(x in app_name for x in server_keywords) or any(any(kw in url for kw in server_keywords) for url in urls):
        return "server"

    browser_apps = ["chrome.exe", "firefox.exe", "edge.exe", "brave.exe"]
    if any(x in app_name for x in browser_apps):
        return "browser"

    return "uncategorized"


@app.get("/api/activity-data/{developer_id}")
def get_activity_data(
    developer_id: str,
    start_date: str = Query(..., description="Start date in ISO format"),
    end_date: str = Query(..., description="End date in ISO format")
):
    try:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        session = SessionLocal()
        query = text("""
            SELECT activity_data, created_at
            FROM activity_records
            WHERE developer_id = :dev
              AND created_at BETWEEN :start AND :end
            ORDER BY created_at ASC
        """)
        result = session.execute(query, {"dev": developer_id, "start": start, "end": end}).fetchall()
        session.close()

        all_activities = []

        for row in result:
            activities = row["activity_data"]
            if isinstance(activities, str):
                activities = json.loads(activities)

            for act in activities:
                project_name = act.get("project_name") or act.get("window_title") or "General Work"
                project_type = act.get("project_type") or "General"
                project_file = act.get("project_file") or act.get("application_name") or "Unknown"
                detailed_activity = act.get("detailed_activity") or act.get("window_title") or project_name
                category = categorize_activity(act)

                all_activities.append({
                    "developer_id": developer_id,
                    "developer_name": developer_id.replace("_", " ").title(),
                    "application_name": act.get("application_name"),
                    "window_title": act.get("window_title"),
                    "duration": act.get("duration", 0),
                    "timestamp": row["created_at"].isoformat(),
                    "category": category,
                    "detailed_activity": detailed_activity,
                    "url": act.get("url") or "",
                    "file_path": act.get("file_path") or "",
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_file": project_file,
                    "subcategory": act.get("subcategory") or "general",
                    "category_confidence": act.get("category_confidence") or 0
                })

        return {"data": all_activities}

    except Exception as e:
        print("Error fetching activity data:", e)
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
