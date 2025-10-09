from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import os
import sys
def extract_app_from_activity_json(activity_data):


# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.activity_analyzer import ActivityAnalyzer

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)

# Database configuration - update with your credentials
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'timesheet_db',
    'user': 'postgres',
    'password': 'your_password'
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

@app.route('/api/activity-data/<developer_id>')
def get_developer_activity_data(developer_id):
    """Get detailed activity data for a specific developer"""
    try:
        # Get date range (default to today)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        # Query activities
        with get_db_connection() as conn:
            activities = conn.execute(
                """
                SELECT 
                    id,
                    application_name,
                    window_title,
                    url,
                    duration,
                    timestamp,
                    category,
                    productive
                FROM activity_records
                WHERE developer_id = ? 
                AND timestamp >= ? 
                AND timestamp < ?
                ORDER BY timestamp DESC
                """,
                (developer_id, start_date, end_date)
            ).fetchall()
            
            # Initialize categories
            activities_by_category = {
                'productivity': [],
                'server': [],
                'unproductive': [],
                'browser': [],
                'system': [],
                'other': []
            }
            
            total_duration = 0
            productive_duration = 0
            
            for activity in activities:
                # Determine category if not set
                if not activity['category']:
                    app_name = (activity['application_name'] or '').lower()
                    title = (activity['window_title'] or '').lower()
                    
                    if any(x in app_name for x in ['code', 'cursor', 'terminal', 'pycharm']):
                        category = 'productivity'
                    elif any(x in app_name for x in ['chrome', 'firefox', 'edge']):
                        if any(x in title for x in ['aws', 'azure', 'github', 'localhost']):
                            category = 'server'
                        elif any(x in title for x in ['youtube', 'facebook', 'instagram']):
                            category = 'unproductive'
                        else:
                            category = 'browser'
                    elif 'explorer' in app_name:
                        category = 'system'
                    else:
                        category = 'other'
                else:
                    category = activity['category']
                
                # Ensure category exists in our dict
                if category not in activities_by_category:
                    category = 'other'
                
                # Add to appropriate category
                activity_data = {
                    'id': activity['id'],
                    'application_name': activity['application_name'] or 'Unknown',
                    'window_title': activity['window_title'] or '',
                    'url': activity['url'] or '',
                    'duration': float(activity['duration']) if activity['duration'] else 60.0,
                    'timestamp': activity['timestamp'].isoformat() if activity['timestamp'] else None,
                    'category': category
                }
                
                activities_by_category[category].append(activity_data)
                
                # Calculate totals
                duration = float(activity['duration']) if activity['duration'] else 60.0
                total_duration += duration
                
                if category in ['productivity', 'server']:
                    productive_duration += duration
            
            # Calculate productivity percentage
            productivity_percentage = (productive_duration / total_duration * 100) if total_duration > 0 else 0
            
            return jsonify({
                'developer_id': developer_id,
                'date': date_str,
                'total_activities': len(activities),
                'total_hours': total_duration / 3600,  # Convert seconds to hours
                'productive_hours': productive_duration / 3600,
                'productivity_percentage': round(productivity_percentage, 2),
                'activities_by_category': activities_by_category,
                'category_summary': {
                    cat: {
                        'count': len(acts),
                        'hours': sum(a['duration'] for a in acts) / 3600,
                        'percentage': (sum(a['duration'] for a in acts) / total_duration * 100) if total_duration > 0 else 0
                    }
                    for cat, acts in activities_by_category.items()
                }
            })
            
    except Exception as e:
        print(f"Error in get_developer_activity_data: {str(e)}")
        return jsonify({
            'error': str(e),
            'developer_id': developer_id,
            'total_activities': 0,
            'total_hours': 0,
            'activities_by_category': {
                'productivity': [],
                'server': [],
                'unproductive': [],
                'browser': [],
                'system': [],
                'other': []
            }
        }), 200  # Return 200 with empty data instead of error

# Also add this endpoint if missing
@app.route('/api/developers-orm')
def get_developers_orm():
    """Get all developers using ORM"""
    try:
        developers = Developer.query.all()
        return jsonify([{
            'id': dev.id,
            'name': dev.name,
            'email': dev.email,
            'team_id': dev.team_id
        } for dev in developers])
    except Exception as e:
        # Fallback to direct SQL if ORM fails
        with get_db_connection() as conn:
            developers = conn.execute("SELECT * FROM developers").fetchall()
            return jsonify([dict(dev) for dev in developers])
if __name__ == '__main__':
    app.run(debug=True, port=5001)
