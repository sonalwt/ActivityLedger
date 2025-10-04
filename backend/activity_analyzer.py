# Database query to fetch and categorize activities
import psycopg2
from datetime import datetime, timedelta
import json
from collections import defaultdict

class ActivityAnalyzer:
    def __init__(self, db_config):
        self.db_config = db_config
        
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def categorize_activity(self, app, title):
        """Categorize activity based on app and title"""
        app_lower = app.lower() if app else ""
        title_lower = title.lower() if title else ""
        
        # Project work (VS Code)
        if "code.exe" in app_lower or "code" in app_lower or "visual studio" in title_lower:
            # Try to extract project name from title
            if " - " in title:
                project_parts = title.split(" - ")
                if len(project_parts) > 1:
                    return "project", project_parts[0].strip()
            return "project", "Unknown Project"
        
        # Browser activities
        elif "chrome.exe" in app_lower or "firefox.exe" in app_lower or "edge.exe" in app_lower:
            # Check for cloud services
            cloud_services = {
                "aws": "AWS",
                "amazon web services": "AWS",
                "ec2": "AWS",
                "s3": "AWS",
                "azure": "Azure",
                "microsoft azure": "Azure",
                "google cloud": "Google Cloud",
                "gcp": "Google Cloud",
                "firebase": "Google Cloud",
                "digitalocean": "DigitalOcean",
                "heroku": "Heroku"
            }
            
            for keyword, service in cloud_services.items():
                if keyword in title_lower:
                    return "cloud", service
            
            # Check for development related sites
            dev_sites = ["github", "gitlab", "stackoverflow", "localhost", "127.0.0.1", ":3000", ":8000", ":8080", ":5000"]
            for site in dev_sites:
                if site in title_lower:
                    return "development", title.split(" - ")[-1] if " - " in title else "Development Site"
            
            # General browsing
            return "browsing", title.split(" - ")[-1] if " - " in title else "Web Browsing"
        
        # File Explorer
        elif "explorer.exe" in app_lower:
            return "file_management", "File Explorer"
        
        # Communication tools
        elif any(tool in app_lower for tool in ["slack", "teams", "discord", "zoom"]):
            return "communication", app.replace(".exe", "").title()
        
        # Other applications
        else:
            return "other", app.replace(".exe", "").title() if app else "Unknown"
    
    def get_developer_activities(self, developer_id, start_date=None, end_date=None):
        """Fetch and analyze activities for a developer"""
        if not start_date:
            start_date = datetime.now().date()
        if not end_date:
            end_date = start_date
            
        query = """
        SELECT app, title, timestamp, duration
        FROM activity_records
        WHERE developer_id = %s 
        AND DATE(timestamp) BETWEEN %s AND %s
        ORDER BY timestamp
        """
        
        activities = defaultdict(lambda: defaultdict(float))
        total_duration = 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (developer_id, start_date, end_date))
                    
                    for row in cursor.fetchall():
                        app, title, timestamp, duration = row
                        if duration is None:
                            duration = 0
                        
                        category, detail = self.categorize_activity(app, title)
                        activities[category][detail] += duration
                        total_duration += duration
        
        except Exception as e:
            print(f"Error fetching activities: {e}")
            
        return activities, total_duration
    
    def calculate_productivity_score(self, activities, total_duration):
        """Calculate productivity score based on activity types"""
        if total_duration == 0:
            return 0
        
        productive_categories = {
            'project': 1.0,      # 100% productive
            'cloud': 0.9,        # 90% productive
            'development': 0.8,  # 80% productive
            'communication': 0.5, # 50% productive
            'file_management': 0.3, # 30% productive
            'browsing': 0.2,     # 20% productive
            'other': 0.1         # 10% productive
        }
        
        productivity_score = 0
        for category, details in activities.items():
            category_duration = sum(details.values())
            weight = productive_categories.get(category, 0.1)
            productivity_score += (category_duration / total_duration) * weight * 100
            
        return round(productivity_score, 2)
    
    def get_dashboard_data(self, developer_id, date=None):
        """Get complete dashboard data for a developer"""
        if not date:
            date = datetime.now().date()
            
        activities, total_duration = self.get_developer_activities(developer_id, date, date)
        productivity_score = self.calculate_productivity_score(activities, total_duration)
        
        # Format data for charts
        chart_data = {
            'categories': [],
            'data': [],
            'details': {}
        }
        
        category_totals = {}
        for category, details in activities.items():
            category_total = sum(details.values())
            category_totals[category] = category_total
            chart_data['details'][category] = [
                {'name': name, 'duration': duration} 
                for name, duration in sorted(details.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        
        # Sort categories by total duration
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        for category, duration in sorted_categories:
            chart_data['categories'].append(category.replace('_', ' ').title())
            chart_data['data'].append(round(duration / 60, 2))  # Convert to minutes
        
        return {
            'chart_data': chart_data,
            'productivity_score': productivity_score,
            'total_duration': round(total_duration / 60, 2),  # Convert to minutes
            'date': date.strftime('%Y-%m-%d')
        }
