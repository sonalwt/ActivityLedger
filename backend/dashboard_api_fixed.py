from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.activity_analyzer_fixed import ActivityAnalyzer

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

@app.route('/api/dashboard/<path:developer_id>')
def get_dashboard_data(developer_id):
    """Get dashboard data for a specific developer"""
    # Ensure developer_id is treated as string
    developer_id = str(developer_id)
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
        print(f"Dashboard error for developer '{developer_id}': {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/productivity/<path:developer_id>/weekly')
def get_weekly_productivity(developer_id):
    """Get weekly productivity trend"""
    # Ensure developer_id is treated as string
    developer_id = str(developer_id)
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
        print(f"Weekly productivity error for developer '{developer_id}': {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/developers')
def get_developers():
    """Get list of all developers - Fixed for VARCHAR developer_id"""
    # Use CAST to ensure string comparison
    query = """
    SELECT DISTINCT 
        CAST(developer_id AS VARCHAR) as id,
        CAST(developer_id AS VARCHAR) as display_name
    FROM activity_records
    WHERE developer_id IS NOT NULL 
        AND CAST(developer_id AS VARCHAR) != ''
        AND LENGTH(TRIM(CAST(developer_id AS VARCHAR))) > 0
    ORDER BY CAST(developer_id AS VARCHAR)
    """
    
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                print("Executing developers query...")
                cursor.execute(query)
                rows = cursor.fetchall()
                print(f"Found {len(rows)} developers")
                
                developers = []
                for row in rows:
                    dev_id = str(row[0])  # Ensure it's a string
                    name = f"Developer {dev_id}"
                    
                    developers.append({
                        'id': dev_id,
                        'name': name
                    })
                    print(f"  - Developer: {dev_id}")
                
        return jsonify(developers)
    except Exception as e:
        print(f"Error fetching developers: {e}")
        import traceback
        traceback.print_exc()
        
        # Try a simpler query as fallback
        try:
            print("Trying fallback query...")
            with analyzer.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Even simpler query - just get raw data
                    cursor.execute("""
                        SELECT DISTINCT developer_id::text 
                        FROM activity_records 
                        WHERE developer_id IS NOT NULL
                        ORDER BY 1
                    """)
                    
                    developers = []
                    for row in cursor.fetchall():
                        if row[0]:  # Check not null
                            dev_id = str(row[0])
                            developers.append({
                                'id': dev_id,
                                'name': f'Developer {dev_id}'
                            })
                    
                    print(f"Fallback query found {len(developers)} developers")
                    return jsonify(developers)
        except Exception as e2:
            print(f"Fallback query also failed: {e2}")
            return jsonify({'error': f'Database error: {str(e2)}'}), 500

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
                
                # Get sample developer IDs with proper casting
                cursor.execute("""
                    SELECT DISTINCT CAST(developer_id AS VARCHAR) as dev_id
                    FROM activity_records 
                    WHERE developer_id IS NOT NULL 
                    ORDER BY 1
                    LIMIT 5
                """)
                sample_devs = [str(row[0]) for row in cursor.fetchall()]
                
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
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/sample-data/<path:developer_id>')
def get_sample_data(developer_id):
    """Get sample data for a developer to debug issues"""
    developer_id = str(developer_id)  # Ensure string
    try:
        query = """
        SELECT CAST(developer_id AS VARCHAR), app, title, timestamp, duration
        FROM activity_records
        WHERE CAST(developer_id AS VARCHAR) = %s
        ORDER BY timestamp DESC
        LIMIT 10
        """
        
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (developer_id,))
                rows = cursor.fetchall()
                
                data = []
                for row in rows:
                    data.append({
                        'developer_id': str(row[0]),
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
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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
    print("\nIMPORTANT: This version handles VARCHAR developer_id fields correctly")
    
    app.run(debug=debug, port=port, host='0.0.0.0')
