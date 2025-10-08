from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.activity_analyzer import ActivityAnalyzer

# Load environment variables
load_dotenv()

app = Flask(__name__,
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)

# Database configuration from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'timesheet_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Check if password is provided
if not DB_CONFIG['password']:
    print("WARNING: Database password not found in environment variables!")
    print("Please create a .env file with DB_PASSWORD=your_password")

analyzer = ActivityAnalyzer(DB_CONFIG)


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/dashboard/<developer_id>')
def get_dashboard_data(developer_id):
    """Get dashboard data for a specific developer"""
    # developer_id is already a string from the route
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
        print(f"Dashboard error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/productivity/<developer_id>/weekly')
def get_weekly_productivity(developer_id):
    """Get weekly productivity trend"""
    # developer_id is already a string from the route
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
        print(f"Weekly productivity error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/developers')
def get_developers():
    """Get list of all developers"""
    # Query to get unique developer_ids from the activity_records table
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
                rows = cursor.fetchall()

                # Process the results
                developers = []
                for row in rows:
                    dev_id = row[0]
                    # Try to extract a readable name if possible
                    name = f"Developer {dev_id}"

                    developers.append({
                        'id': dev_id,  # Keep as string
                        'name': name
                    })

        return jsonify(developers)
    except Exception as e:
        print(f"Error fetching developers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-connection')
def test_connection():
    """Test database connection"""
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]

                # Get activity records count
                cursor.execute("SELECT COUNT(*) FROM activity_records")
                count = cursor.fetchone()[0]

                # Get sample developer IDs
                cursor.execute("""
                    SELECT DISTINCT developer_id 
                    FROM activity_records 
                    WHERE developer_id IS NOT NULL 
                    LIMIT 5
                """)
                sample_devs = [row[0] for row in cursor.fetchall()]

                # Check data type of developer_id column
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'activity_records' 
                    AND column_name = 'developer_id'
                """)
                data_type = cursor.fetchone()

                return jsonify({
                    'status': 'connected',
                    'database_version': version,
                    'activity_records_count': count,
                    'sample_developer_ids': sample_devs,
                    'developer_id_type': data_type[0] if data_type else 'unknown'
                })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/sample-data/<developer_id>')
def get_sample_data(developer_id):
    """Get sample data for a developer to debug issues"""
    try:
        query = """
        SELECT developer_id, app, title, timestamp, duration
        FROM activity_records
        WHERE developer_id = %s
        ORDER BY timestamp DESC
        LIMIT 10
        """

        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (str(developer_id),))
                rows = cursor.fetchall()

                data = []
                for row in rows:
                    data.append({
                        'developer_id': row[0],
                        'app': row[1],
                        'title': row[2],
                        'timestamp': row[3].isoformat() if row[3] else None,
                        'duration': row[4]
                    })

                return jsonify({
                    'developer_id': developer_id,
                    'sample_count': len(data),
                    'data': data
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@router.get("/activities")
def get_activities():
    # Fetch records from your DB
    records = fetch_from_db()  # Replace with actual DB call
    categorized_records = []

    for rec in records:
        activity_text = " ".join([str(v).lower() for v in rec["activity_data"].values()])
        category = "Non-Productive"

        # Productivity
        if any(app in activity_text for app in ["code.exe", "cpanel", "shareplex", "filezilla"]):
            category = "Productivity"
        # Server
        elif any(k in activity_text for k in ["awz", "google", "gcp", "termius", "azure"]):
            category = "Server"
        # Browser
        elif any(k in activity_text for k in ["youtube", "gmail", "research", "stackoverflow", "github"]):
            category = "Browser"

        rec["category"] = category
        categorized_records.append(rec)

    return categorized_records

return categorized_records
if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5001))
    debug = os.getenv('DEBUG_MODE', 'True').lower() == 'true'

    print(f"Starting dashboard API server on port {port}...")
    print(f"Dashboard URL: http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("\nAPI Endpoints:")
    print(f"  Dashboard: http://localhost:{port}/")
    print(f"  Test Connection: http://localhost:{port}/api/test-connection")
    print(f"  Developers List: http://localhost:{port}/api/developers")

    app.run(debug=debug, port=port, host='0.0.0.0')
