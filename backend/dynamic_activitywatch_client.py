# backend/dynamic_activitywatch_client.py
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DynamicActivityWatchClient:
    """ActivityWatch client that works with dynamically discovered developers"""
    
    def __init__(self, developer_info: Dict):
        self.developer_info = developer_info
        self.developer_id = developer_info['id']
        self.host = developer_info['host']
        self.port = developer_info['port']
        self.base_url = f"https://{self.host}:{self.port}"
        self.device_id = developer_info.get('device_id', self.developer_id)
        self.timeout = 10
        
    def test_connection(self) -> bool:
        """Test connection to ActivityWatch server"""
        try:
            response = requests.get(f"{self.base_url}/api/0/info", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_buckets(self) -> Dict:
        """Get all available buckets"""
        try:
            response = requests.get(f"{self.base_url}/api/0/buckets", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting buckets: {e}")
            return {}
    
    def get_events(self, bucket_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events from a specific bucket"""
        try:
            params = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            response = requests.get(
                f"{self.base_url}/api/0/buckets/{bucket_id}/events", 
                params=params, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting events from {bucket_id}: {e}")
            return []
    
    def get_activity_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get processed activity data"""
        try:
            buckets = self.get_buckets()
            if not buckets:
                logger.warning(f"No buckets found for {self.developer_id}")
                return []
            
            # Get window and application buckets
            window_buckets = [name for name in buckets.keys() if 'window' in name.lower()]
            app_buckets = [name for name in buckets.keys() if 'afk' not in name.lower() and name not in window_buckets]
            
            logger.info(f"Found buckets for {self.developer_id}: {len(window_buckets)} window, {len(app_buckets)} other")
            
            activities = []
            
            # Process window buckets (primary data source)
            for bucket_name in window_buckets:
                events = self.get_events(bucket_name, start_time, end_time)
                logger.info(f"Retrieved {len(events)} events from {bucket_name}")
                
                for event in events:
                    data = event.get('data', {})
                    
                    # Parse timestamp
                    timestamp_str = event.get('timestamp', '')
                    try:
                        if timestamp_str:
                            # Handle different timestamp formats
                            if timestamp_str.endswith('Z'):
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            elif '+' in timestamp_str or '-' in timestamp_str[-6:]:
                                timestamp = datetime.fromisoformat(timestamp_str)
                            else:
                                timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
                        else:
                            timestamp = start_time
                    except Exception as e:
                        logger.warning(f"Error parsing timestamp {timestamp_str}: {e}")
                        timestamp = start_time
                    
                    duration = event.get('duration', 0)
                    if duration < 1:  # Skip very short activities (< 1 second)
                        continue
                    
                    activity = {
                        'developer_id': self.developer_id,
                        'developer_name': self.developer_info['name'],
                        'developer_hostname': self.developer_info['hostname'],
                        'application_name': data.get('app', data.get('application', 'Unknown')),
                        'window_title': data.get('title', ''),
                        'duration': duration,
                        'timestamp': timestamp.isoformat(),
                        'category': self._categorize_activity(data.get('app', '')),
                        'detailed_activity': self._get_detailed_activity(data),
                        'url': data.get('url', ''),
                        'file_path': self._extract_file_path(data.get('title', '')),
                        'bucket_name': bucket_name,
                        'device_id': self.device_id,
                        'activity_timestamp': timestamp  # For database storage
                    }
                    activities.append(activity)
            
            # If no window data, try other buckets
            if not activities and app_buckets:
                logger.info(f"No window data found, trying other buckets: {app_buckets}")
                for bucket_name in app_buckets[:3]:  # Limit to first 3 to avoid too much data
                    events = self.get_events(bucket_name, start_time, end_time)
                    logger.info(f"Retrieved {len(events)} events from {bucket_name}")
                    
                    for event in events:
                        data = event.get('data', {})
                        duration = event.get('duration', 0)
                        
                        if duration < 5:  # Skip very short activities
                            continue
                        
                        timestamp_str = event.get('timestamp', '')
                        try:
                            if timestamp_str:
                                if timestamp_str.endswith('Z'):
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                else:
                                    timestamp = datetime.fromisoformat(timestamp_str)
                            else:
                                timestamp = start_time
                        except:
                            timestamp = start_time
                        
                        activities.append({
                            'developer_id': self.developer_id,
                            'developer_name': self.developer_info['name'],
                            'developer_hostname': self.developer_info['hostname'],
                            'application_name': data.get('app', str(data)),
                            'window_title': str(data),
                            'duration': duration,
                            'timestamp': timestamp.isoformat(),
                            'category': self._categorize_activity(data.get('app', '')),
                            'detailed_activity': f"Activity from {bucket_name}",
                            'url': '',
                            'file_path': '',
                            'bucket_name': bucket_name,
                            'device_id': self.device_id,
                            'activity_timestamp': timestamp
                        })
            
            # Sort by duration (highest first)
            activities.sort(key=lambda x: x['duration'], reverse=True)
            
            logger.info(f"Processed {len(activities)} activities for {self.developer_id}")
            return activities
        
        except Exception as e:
            logger.error(f"Error getting activity data for {self.developer_id}: {e}")
            return []
    
    def _categorize_activity(self, app_name: str) -> str:
        """Categorize activity based on application name"""
        if not app_name:
            return 'Other'
            
        app_lower = app_name.lower()
        
        # Development tools
        if any(ide in app_lower for ide in [
            'cursor', 'code', 'vim', 'sublime', 'atom', 'intellij', 
            'pycharm', 'webstorm', 'phpstorm', 'vscode', 'visual studio'
        ]):
            return 'Development'
        
        # Browsers
        elif any(browser in app_lower for browser in [
            'chrome', 'firefox', 'safari', 'edge', 'brave', 'opera'
        ]):
            return 'Web Browsing'
        
        # Communication
        elif any(comm in app_lower for comm in [
            'slack', 'discord', 'teams', 'zoom', 'skype', 'telegram', 'whatsapp'
        ]):
            return 'Communication'
        
        # Terminal/Command Line
        elif any(terminal in app_lower for terminal in [
            'terminal', 'cmd', 'powershell', 'bash', 'zsh', 'iterm'
        ]):
            return 'Development'
        
        # Design tools
        elif any(design in app_lower for design in [
            'figma', 'sketch', 'photoshop', 'illustrator', 'canva'
        ]):
            return 'Design'
        
        # Productivity
        elif any(prod in app_lower for prod in [
            'notion', 'obsidian', 'trello', 'asana', 'jira', 'confluence'
        ]):
            return 'Productivity'
        
        else:
            return 'Other'
    
    def _get_detailed_activity(self, data: Dict) -> str:
        """Get detailed activity description"""
        title = data.get('title', '')
        app = data.get('app', '')
        
        if not title:
            return app or 'Unknown Activity'
        
        # Development-specific details
        if any(ide in app.lower() for ide in ['cursor', 'code', 'vim', 'sublime', 'atom']):
            if any(ext in title.lower() for ext in ['.py', '.js', '.html', '.css', '.json', '.md', '.tsx', '.jsx']):
                return f"Coding: {title}"
            else:
                return f"IDE: {title}"
        
        # Browser-specific details
        elif any(browser in app.lower() for browser in ['chrome', 'firefox', 'safari', 'edge']):
            if data.get('url'):
                domain = self._extract_domain_from_url(data['url'])
                return f"Browsing: {domain}"
            elif 'github' in title.lower():
                return f"GitHub: {title}"
            elif 'stackoverflow' in title.lower():
                return f"StackOverflow: {title}"
            else:
                return f"Web: {title}"
        
        # Communication details
        elif any(comm in app.lower() for comm in ['slack', 'discord', 'teams']):
            return f"Chat: {app}"
        
        return title
    
    def _extract_file_path(self, title: str) -> str:
        """Extract file path from window title if available"""
        if not title:
            return ''
        
        # Common file extensions
        extensions = ['.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.tsx', '.jsx', '.vue', '.php']
        
        if any(ext in title.lower() for ext in extensions):
            # Try to extract path from common patterns
            parts = title.split(' - ')
            if len(parts) > 1:
                # Usually first part contains the file path
                potential_path = parts[0].strip()
                if any(ext in potential_path.lower() for ext in extensions):
                    return potential_path
            
            # Try splitting by other delimiters
            for delimiter in [' — ', ' | ', ' • ']:
                if delimiter in title:
                    parts = title.split(delimiter)
                    for part in parts:
                        if any(ext in part.lower() for ext in extensions):
                            return part.strip()
        
        return ''
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url[:50] + '...' if len(url) > 50 else url
