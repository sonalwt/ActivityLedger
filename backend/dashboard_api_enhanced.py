from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

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

@app.route('/api/dashboard/<int:developer_id>')
def get_dashboard_data(developer_id):
    """Get dashboard data for a specific developer"""
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

@app.route('/api/productivity/<int:developer_id>/weekly')
def get_weekly_productivity(developer_id):
    """Get weekly productivity trend"""
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
    # Modified query to handle the actual table structure
    query = """
    WITH developer_info AS (
        SELECT 
            developer_id,
            MAX(CASE 
                WHEN app LIKE '%sync%' THEN 
                    SUBSTRING(title FROM 'sync.ps1 - timesheet_new - (.+?) - Visual Studio Code')
                ELSE NULL 
            END) as developer_name
        FROM activity_records
        WHERE developer_id IS NOT NULL
        GROUP BY developer_id
    )
    SELECT 
        developer_id as id,
        COALESCE(developer_name, 'Developer ' || developer_id) as name
    FROM developer_info
    ORDER BY developer_id
    """
    
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                developers = [
                    {'id': row[0], 'name': row[1]} 
                    for row in cursor.fetchall()
                ]
        return jsonify(developers)
    except Exception as e:
        print(f"Error fetching developers: {e}")
        # Fallback: try simpler query
        try:
            query = "SELECT DISTINCT developer_id FROM activity_records WHERE developer_id IS NOT NULL ORDER BY developer_id"
            with analyzer.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    developers = [
                        {'id': row[0], 'name': f'Developer {row[0]}'} 
                        for row in cursor.fetchall()
                    ]
            return jsonify(developers)
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

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
                
                return jsonify({
                    'status': 'connected',
                    'database_version': version,
                    'activity_records_count': count
                })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5001))
    debug = os.getenv('DEBUG_MODE', 'True').lower() == 'true'
    
    print(f"Starting dashboard API server on port {port}...")
    print(f"Dashboard URL: http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    app.run(debug=debug, port=port, host='0.0.0.0')
