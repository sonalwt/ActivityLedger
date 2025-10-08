# add_date_endpoints.py
# Add these endpoints to your dashboard_api_fixed.py

"""
Add these endpoints to your dashboard_api_fixed.py file:

@app.route('/api/latest-data-date')
def get_latest_data_date():
    '''Get the latest date that has activity data'''
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT MAX(DATE(timestamp)) as latest_date
                    FROM activity_records
                    WHERE duration > 0
                ''')
                result = cursor.fetchone()
                
                if result and result[0]:
                    return jsonify({
                        'latest_date': result[0].isoformat(),
                        'has_data': True
                    })
                else:
                    return jsonify({
                        'latest_date': None,
                        'has_data': False
                    })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/developer-dates/<path:developer_id>')
def get_developer_dates(developer_id):
    '''Get all dates that have data for a specific developer'''
    developer_id = str(developer_id)
    try:
        with analyzer.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT DISTINCT DATE(timestamp) as activity_date
                    FROM activity_records
                    WHERE CAST(developer_id AS VARCHAR) = %s
                    AND duration > 0
                    ORDER BY activity_date DESC
                ''', (developer_id,))
                
                dates = [row[0].isoformat() for row in cursor.fetchall()]
                
                return jsonify({
                    'developer_id': developer_id,
                    'available_dates': dates,
                    'count': len(dates)
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

print("=" * 60)
print("ENHANCED DASHBOARD API ENDPOINTS")
print("=" * 60)
print("\nTo make your dashboard automatically show the correct date,")
print("add the endpoints shown above to your dashboard_api_fixed.py file.")
print("\nThen replace dashboard.js with dashboard_auto_date.js:")
print("1. Rename dashboard.js to dashboard_original.js")
print("2. Rename dashboard_auto_date.js to dashboard.js")
print("\nThis will make the dashboard automatically load the latest")
print("date with data instead of defaulting to today.")
print("=" * 60)
