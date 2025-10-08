# activity_analyzer_fixed.py
# Activity analyzer module for dashboard API

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
import json
from typing import List, Dict, Tuple, Optional

class ActivityAnalyzer:
    """Analyze activity data for dashboard display"""
    
    def __init__(self, db_config: Dict[str, any]):
        self.db_config = db_config
        
    def get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
    
    def get_developer_activities(self, developer_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Tuple[List[Dict], float]:
        """Get activities for a specific developer within date range"""
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.today()
            
        query = """
            SELECT 
                application_name,
                window_title,
                category,
                duration,
                timestamp,
                project_name,
                url
            FROM activity_records
            WHERE CAST(developer_id AS VARCHAR) = %s
            AND DATE(timestamp) BETWEEN %s AND %s
            AND application_name IS NOT NULL
            ORDER BY timestamp DESC
        """
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (developer_id, start_date, end_date))
                activities = cursor.fetchall()
                
                # Calculate total duration
                total_duration = sum(act['duration'] or 0 for act in activities)
                
                return activities, total_duration
    
    def calculate_productivity_score(self, activities: List[Dict], total_duration: float) -> int:
        """Calculate productivity score based on activities"""
        if not activities or total_duration == 0:
            return 0
            
        productive_time = 0
        productive_categories = ['ide', 'database', 'documentation']
        
        for activity in activities:
            if activity.get('category') in productive_categories:
                productive_time += activity.get('duration', 0)
            # Also consider specific applications
            elif activity.get('application_name', '').lower() in ['code', 'vscode', 'sublime', 'pycharm']:
                productive_time += activity.get('duration', 0)
                
        # Calculate percentage
        score = int((productive_time / total_duration) * 100)
        return min(score, 100)  # Cap at 100%
    
    def get_dashboard_data(self, developer_id: str, target_date: Optional[date] = None) -> Dict:
        """Get comprehensive dashboard data for a developer"""
        if not target_date:
            target_date = date.today()
            
        # Get activities for the day
        activities, total_duration = self.get_developer_activities(developer_id, target_date, target_date)
        
        # Calculate productivity score
        productivity_score = self.calculate_productivity_score(activities, total_duration)
        
        # Get active developers count
        active_devs = self._get_active_developers_count(target_date)
        
        # Calculate hours
        total_hours = total_duration / 3600 if total_duration else 0
        
        # Get top applications
        app_breakdown = self._get_application_breakdown(activities)
        
        # Get activity timeline
        timeline = self._get_activity_timeline(activities)
        
        return {
            'developer_id': developer_id,
            'date': target_date.isoformat(),
            'active_developers': active_devs,
            'team_productivity': productivity_score,
            'total_hours': round(total_hours, 1),
            'avg_hours_per_dev': round(total_hours, 1),  # For single dev, same as total
            'application_breakdown': app_breakdown,
            'activity_timeline': timeline,
            'developer_stats': {
                developer_id: {
                    'hours': round(total_hours, 1),
                    'productivity': productivity_score,
                    'status': 'active' if total_hours > 0 else 'offline'
                }
            }
        }
    
    def _get_active_developers_count(self, target_date: date) -> int:
        """Get count of active developers for a date"""
        query = """
            SELECT COUNT(DISTINCT developer_id) 
            FROM activity_records
            WHERE DATE(timestamp) = %s
            AND duration > 0
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (target_date,))
                result = cursor.fetchone()
                return result[0] if result else 0
    
    def _get_application_breakdown(self, activities: List[Dict]) -> List[Dict]:
        """Get breakdown of time spent per application"""
        app_time = {}
        
        for activity in activities:
            app_name = activity.get('application_name', 'Unknown')
            duration = activity.get('duration', 0)
            
            if app_name in app_time:
                app_time[app_name] += duration
            else:
                app_time[app_name] = duration
        
        # Convert to list and sort by duration
        breakdown = [
            {
                'name': app,
                'value': round(duration / 3600, 2),  # Convert to hours
                'percentage': round((duration / sum(app_time.values())) * 100, 1) if app_time else 0
            }
            for app, duration in app_time.items()
        ]
        
        return sorted(breakdown, key=lambda x: x['value'], reverse=True)[:10]  # Top 10
    
    def _get_activity_timeline(self, activities: List[Dict]) -> List[Dict]:
        """Get hourly activity timeline"""
        hourly_data = {}
        
        for activity in activities:
            timestamp = activity.get('timestamp')
            if timestamp:
                hour = timestamp.hour
                duration = activity.get('duration', 0)
                
                if hour in hourly_data:
                    hourly_data[hour] += duration
                else:
                    hourly_data[hour] = duration
        
        # Create timeline for all hours (0-23)
        timeline = []
        for hour in range(24):
            timeline.append({
                'hour': f"{hour:02d}:00",
                'value': round(hourly_data.get(hour, 0) / 3600, 2)  # Convert to hours
            })
        
        return timeline
