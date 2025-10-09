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

@app.route('/api/activity-data/<developer_name>')
def get_developer_activity_data(developer_name):
    """Get activity data - simplified since we know the exact format"""
    try:
        from datetime import datetime, timedelta
        import json
        
        # Get date range (default to today)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        print(f"Looking for developer: '{developer_name}' on date: {date_str}")
        
        with get_db_connection() as conn:
            # Since we know the database has 'riddhidhakhara' (no spaces, lowercase)
            # Just use the name directly!
            
            # First, verify the developer exists
            check = conn.execute("""
                SELECT COUNT(*) as count
                FROM activity_records
                WHERE developer_id = ?
                AND DATE(timestamp) = DATE(?)
            """, (developer_name, start_date)).fetchone()
            
            print(f"Found {check['count']} records for {developer_name} on {date_str}")
            
            # Get activities - use exact match
            activities = conn.execute("""
                SELECT 
                    id,
                    activity_data,
                    window_title,
                    url,
                    duration,
                    timestamp,
                    category,
                    productive,
                    developer_id
                FROM activity_records
                WHERE developer_id = ?
                AND timestamp >= ? 
                AND timestamp < ?
                ORDER BY timestamp DESC
            """, (developer_name, start_date, end_date)).fetchall()
            
            print(f"Query returned {len(activities)} activities")
            
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
            
            # Helper function to extract app from JSON
            def extract_app_from_json(activity_data):
                try:
                    if isinstance(activity_data, str):
                        data = json.loads(activity_data)
                    else:
                        data = activity_data
                    
                    if 'app' in data:
                        return data['app']
                    elif 'data' in data and isinstance(data['data'], dict):
                        if 'app' in data['data']:
                            return data['data']['app']
                    return None
                except:
                    return None
            
            for activity in activities:
                # Extract app name from JSON
                app_name = extract_app_from_json(activity['activity_data']) if activity['activity_data'] else None
                
                # Use existing category or determine new one
                category = activity['category'] if activity['category'] else 'other'
                
                # Ensure category exists in our dict
                if category not in activities_by_category:
                    category = 'other'
                
                # Add to appropriate category
                activity_data = {
                    'id': activity['id'],
                    'application_name': app_name or 'Unknown',
                    'window_title': activity['window_title'] or '',
                    'url': activity['url'] or '',
                    'duration': float(activity['duration']) if activity['duration'] else 0,
                    'timestamp': activity['timestamp'].isoformat() if activity['timestamp'] else None,
                    'category': category
                }
                
                activities_by_category[category].append(activity_data)
                
                # Calculate totals
                duration = float(activity['duration']) if activity['duration'] else 0
                total_duration += duration
                
                if category in ['productivity', 'server']:
                    productive_duration += duration
            
            # Calculate productivity percentage
            productivity_percentage = (productive_duration / total_duration * 100) if total_duration > 0 else 0
            
            return jsonify({
                'developer_name': developer_name,
                'actual_name': developer_name,
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
        import traceback
        print(f"Error in get_developer_activity_data: {str(e)}")
        print(f"Developer name: {developer_name}")
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'developer_name': developer_name,
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
        }), 200

# Update developers endpoint to return exact names
@app.route('/api/developers-orm')
def get_developers_orm():
    """Get all developers - return exact names as in database"""
    try:
        with get_db_connection() as conn:
            # Get unique developer names exactly as they are
            result = conn.execute("""
                SELECT DISTINCT developer_id, COUNT(*) as activity_count
                FROM activity_records
                WHERE developer_id IS NOT NULL AND developer_id != ''
                GROUP BY developer_id
                ORDER BY developer_id
            """).fetchall()
            
            developers = []
            for idx, row in enumerate(result):
                developer_id = row['developer_id']
                
                # For display, convert to title case
                display_name = ' '.join(word.capitalize() for word in developer_id.replace('.', ' ').split())
                
                developers.append({
                    'id': developer_id,  # Use exact database format: riddhidhakhara
                    'name': display_name,  # Display as: Riddhidhakhara
                    'email': f'{developer_id}@company.com',
                    'team_id': 1,
                    'activity_count': row['activity_count']
                })
            
            return jsonify(developers)
    except Exception as e:
        print(f"Error in get_developers_orm: {str(e)}")
        return jsonify([]), 200

# Add debug endpoint to verify data
@app.route('/api/debug/check-developer/<developer_name>')
def check_developer(developer_name):
    """Debug endpoint to check developer data"""
    try:
        with get_db_connection() as conn:
            # Check exact match
            exact = conn.execute("""
                SELECT developer_id, COUNT(*) as count, 
                       MIN(timestamp) as first_activity,
                       MAX(timestamp) as last_activity
                FROM activity_records
                WHERE developer_id = ?
                GROUP BY developer_id
            """, (developer_name,)).fetchone()
            
            # Check similar
            similar = conn.execute("""
                SELECT DISTINCT developer_id
                FROM activity_records
                WHERE developer_id LIKE ?
                LIMIT 10
            """, (f'%{developer_name[:5]}%',)).fetchall()
            
            return jsonify({
                'searched_for': developer_name,
                'exact_match': {
                    'found': exact is not None,
                    'count': exact['count'] if exact else 0,
                    'first_activity': str(exact['first_activity']) if exact else None,
                    'last_activity': str(exact['last_activity']) if exact else None
                },
                'similar_names': [row['developer_id'] for row in similar]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
