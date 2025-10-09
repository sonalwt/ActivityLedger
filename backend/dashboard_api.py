from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
def extract_app_from_activity_json(activity_data):


# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.activity_analyzer import ActivityAnalyzer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration - update with your credentials
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'timesheet',
    'user': 'postgres',
    'password': 'asdf1234'
}

analyzer = ActivityAnalyzer(DB_CONFIG)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/dashboard/<developer_id>')
def get_dashboard_data(developer_id):
    """Get dashboard data for a specific developer"""
    # developer_id comes as string from route
    date_str = request.args.get('date')
    
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    else:
        date = None
    
    try:
        data = analyzer.get_dashboard_data(developer_id, date)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/productivity/<developer_id>/weekly')
def get_weekly_productivity(developer_id):
    """Get weekly productivity trend"""
    # developer_id comes as string from route
    try:
        from datetime import timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        weekly_data = []
        dates = []
        scores = []
        
        current_date = start_date
        while current_date <= end_date:
            activities, total_duration = analyzer.get_developer_activities(
                developer_id, current_date, current_date
            )
            score = analyzer.calculate_productivity_score(activities, total_duration)
            
            dates.append(current_date.strftime('%a'))
            scores.append(score)
            current_date += timedelta(days=1)
        
        return jsonify({
            'dates': dates,
            'scores': scores
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/developers')
def get_developers():
    """Get list of all developers"""
    query = """
    SELECT DISTINCT 
        developer_id,
        developer_id as name
    FROM activity_records
    WHERE developer_id IS NOT NULL AND developer_id != ''
    ORDER BY developer_id
    """
    
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                developers = [
                    {'id': row[0], 'name': f'Developer {row[0]}'} 
                    for row in cursor.fetchall()
                ]
        return jsonify(developers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# Update your dashboard_api.py to handle both date formats

def categorize_activity(activity: dict) -> str:
    app_name = (activity.get("application_name") or "").lower()
    window_title = (activity.get("window_title") or "").lower()
    urls = [url.lower() for url in activity.get("urls") or []]

    # System lock or entertainment filters
    if any(x in window_title for x in ["lock", "locked"]) or any(x in app_name for x in ["lockapp", "logonui"]):
        return "non-work"
    if any(x in window_title for x in ["youtube", "netflix", "spotify", "music"]):
        return "non-work"

    # Productivity apps
    productivity_apps = ["vscode", "code.exe", "pycharm", "intellij", "sublime", "atom", "notepad++", "vim", "emacs", "notion", "jira", "trello", "figma", "photoshop"]
    if any(x in app_name for x in productivity_apps):
        return "productivity"

    # Server / Admin apps
    server_keywords = ["aws", "azure", "gcp", "plesk", "cpanel", "whm", "directadmin", "webmin", "ssh", "putty", "filezilla", "localhost", "127.0.0.1", "digitalocean", "linode"]
    if any(x in app_name for x in server_keywords) or any(any(kw in url for kw in server_keywords) for url in urls):
        return "server"

    # Browser apps
    browser_apps = ["chrome.exe", "firefox.exe", "edge.exe", "brave.exe"]
    if any(x in app_name for x in browser_apps):
        return "browser"

    # Fallback
    return "uncategorized"

# Endpoint@app.get("/api/activity-data/{developer_id}")
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

        # Categorization rules
        productivity_keywords = ["code.exe", "cpanel", "shareplex", "filezilla"]
        server_keywords = ["aws", "google", "gcp", "termius", "azure"]
        browser_keywords = ["youtube", "gmail", "research", "stackoverflow", "github"]

        all_activities = []

        for row in result:
            activities = row["activity_data"]
            if isinstance(activities, str):
                activities = json.loads(activities)  # convert string JSON to Python list

            for act in activities:
                app_name = str(act.get("app", "")).lower()
                title = str(act.get("title", "")).lower()

                category = "other"
                if any(k in app_name for k in productivity_keywords):
                    category = "productivity"
                elif "chrome.exe" in app_name and any(k in title for k in server_keywords):
                    category = "server"
                elif any(k in title for k in browser_keywords):
                    category = "browser"

                all_activities.append({
                    "timestamp": row["created_at"].isoformat(),
                    "app": act.get("app"),
                    "title": act.get("title"),
                    "duration": act.get("duration", 0),
                    "category": category
                })

        return {"data": all_activities}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
