# Update your dashboard_api.py with this dynamic solution

@app.route('/api/activity-data/<developer_name>')
def get_developer_activity_data(developer_name):
    """Get activity data for a developer by name (handles various name formats)"""
    try:
        from datetime import datetime, timedelta
        import json
        
        # Get date range (default to today)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        with get_db_connection() as conn:
            # First, let's find what exact name format is in the database
            # Convert frontend format (riddhi.dhakhara) to possible database formats
            
            # Split the name
            name_parts = developer_name.split('.')
            
            # Generate possible name formats
            possible_formats = [
                developer_name,                                    # riddhi.dhakhara
                developer_name.replace('.', '_'),                  # riddhi_dhakhara
                developer_name.replace('.', ' '),                  # riddhi dhakhara
                ' '.join(name_parts),                             # riddhi dhakhara
                ' '.join(name_parts).title(),                     # Riddhi Dhakhara
                ' '.join(name_parts).upper(),                     # RIDDHI DHAKHARA
                ' '.join(name_parts).lower(),                     # riddhi dhakhara
                ''.join(name_parts),                              # riddhidhakhara
                ''.join(name_parts).title(),                      # RiddhiDhakhara
                developer_name.title(),                           # Riddhi.Dhakhara
            ]
            
            # Try to find the exact format used in activity_records
            actual_developer_name = None
            for format_name in possible_formats:
                check_result = conn.execute(
                    """
                    SELECT DISTINCT developer_id 
                    FROM activity_records 
                    WHERE LOWER(developer_id) = LOWER(?)
                    LIMIT 1
                    """,
                    (format_name,)
                ).fetchone()
                
                if check_result:
                    actual_developer_name = check_result['developer_id']
                    break
            
            # If still not found, try partial matching
            if not actual_developer_name and name_parts:
                first_name = name_parts[0]
                check_result = conn.execute(
                    """
                    SELECT DISTINCT developer_id 
                    FROM activity_records 
                    WHERE LOWER(developer_id) LIKE LOWER(?)
                    LIMIT 1
                    """,
                    (f'%{first_name}%',)
                ).fetchone()
                
                if check_result:
                    actual_developer_name = check_result['developer_id']
            
            if not actual_developer_name:
                # Log available developer names for debugging
                available_devs = conn.execute("""
                    SELECT DISTINCT developer_id 
                    FROM activity_records 
                    ORDER BY developer_id
                    LIMIT 20
                """).fetchall()
                
                print(f"Developer '{developer_name}' not found. Available developers:")
                for dev in available_devs:
                    print(f"  - {dev['developer_id']}")
                
                # Return empty data
                return jsonify({
                    'developer_name': developer_name,
                    'actual_name': None,
                    'date': date_str,
                    'total_activities': 0,
                    'total_hours': 0,
                    'activities_by_category': {
                        'productivity': [],
                        'server': [],
                        'unproductive': [],
                        'browser': [],
                        'system': [],
                        'other': []
                    },
                    'message': f'Developer {developer_name} not found in activity records'
                })
            
            # Now fetch activities with the correct developer name
            activities = conn.execute(
                """
                SELECT 
                    id,
                    activity_data,
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
                (actual_developer_name, start_date, end_date)
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
            
            # Helper function to extract app from JSON
            def extract_app_from_json(activity_data):
                try:
                    if isinstance(activity_data, str):
                        data = json.loads(activity_data)
                    else:
                        data = activity_data
                    
                    # Try different JSON structures
                    if 'app' in data:
                        return data['app']
                    elif 'data' in data and isinstance(data['data'], dict):
                        if 'app' in data['data']:
                            return data['data']['app']
                        elif 'current_window' in data['data']:
                            window_data = data['data']['current_window']
                            if 'app' in window_data:
                                return window_data['app']
                    elif 'current_window' in data and 'app' in data['current_window']:
                        return data['current_window']['app']
                    
                    return None
                except:
                    return None
            
            for activity in activities:
                # Extract app name from JSON
                app_name = extract_app_from_json(activity['activity_data']) if activity['activity_data'] else None
                
                # Determine category
                if activity['category']:
                    category = activity['category']
                else:
                    app_lower = (app_name or '').lower()
                    title_lower = (activity['window_title'] or '').lower()
                    
                    if any(x in app_lower for x in ['code', 'cursor', 'terminal', 'pycharm']):
                        category = 'productivity'
                    elif any(x in app_lower for x in ['chrome', 'firefox', 'edge', 'brave']):
                        if any(x in title_lower for x in ['aws', 'azure', 'github', 'localhost']):
                            category = 'server'
                        elif any(x in title_lower for x in ['youtube', 'facebook', 'instagram']):
                            category = 'unproductive'
                        else:
                            category = 'browser'
                    elif 'explorer' in app_lower:
                        category = 'system'
                    else:
                        category = 'other'
                
                if category not in activities_by_category:
                    category = 'other'
                
                # Add activity to category
                activity_data = {
                    'id': activity['id'],
                    'application_name': app_name or 'Unknown',
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
                'developer_name': developer_name,
                'actual_name': actual_developer_name,
                'date': date_str,
                'total_activities': len(activities),
                'total_hours': total_duration / 3600,
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

# Also update the developers endpoint to return names in the format your frontend expects
@app.route('/api/developers-orm')
def get_developers_orm():
    """Get all developers - dynamic based on what's in activity_records"""
    try:
        with get_db_connection() as conn:
            # Get unique developer names from activity_records
            developer_names = conn.execute("""
                SELECT DISTINCT developer_id as name, COUNT(*) as activity_count
                FROM activity_records
                WHERE developer_id IS NOT NULL
                GROUP BY developer_id
                ORDER BY developer_id
            """).fetchall()
            
            # Format for frontend compatibility
            developers = []
            for idx, dev in enumerate(developer_names):
                name = dev['name']
                # Convert to frontend format (e.g., "Riddhi Dhakhara" -> "riddhi.dhakhara")
                formatted_id = name.lower().replace(' ', '.')
                
                developers.append({
                    'id': formatted_id,  # Frontend expects this format
                    'name': name,        # Actual name in database
                    'email': f'{formatted_id}@company.com',  # Generated email
                    'team_id': 1,
                    'activity_count': dev['activity_count']
                })
            
            return jsonify(developers)
    except Exception as e:
        print(f"Error in get_developers_orm: {str(e)}")
        return jsonify([]), 200

# Add a debug endpoint to check name formats
@app.route('/api/debug/developer-names')
def debug_developer_names():
    """Debug endpoint to see actual developer names in database"""
    try:
        with get_db_connection() as conn:
            names = conn.execute("""
                SELECT DISTINCT developer_id, COUNT(*) as count
                FROM activity_records
                WHERE developer_id IS NOT NULL
                GROUP BY developer_id
                ORDER BY count DESC
                LIMIT 50
            """).fetchall()
            
            return jsonify([{
                'database_name': name['developer_id'],
                'frontend_format': name['developer_id'].lower().replace(' ', '.'),
                'record_count': name['count']
            } for name in names])
    except Exception as e:
        return jsonify({'error': str(e)}), 500