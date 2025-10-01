# 1. Create developer_discovery.py - Dynamic discovery system

import requests
import socket
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import netifaces

logger = logging.getLogger(__name__)

class DeveloperDiscovery:
    """Automatically discover ActivityWatch instances on network and local machine"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.discovered_developers = []
        self.default_ports = [5600, 5601, 5602, 5603, 5700]  # Common AW ports
        self.timeout = 3  # Connection timeout in seconds
        
    def get_local_networks(self) -> List[str]:
        """Get all local network ranges to scan"""
        networks = []
        try:
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        if 'addr' in addr_info and 'netmask' in addr_info:
                            ip = addr_info['addr']
                            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                # Generate network range (simple /24 assumption)
                                base_ip = '.'.join(ip.split('.')[:-1])
                                networks.append(base_ip)
        except Exception as e:
            logger.warning(f"Could not get network interfaces: {e}")
            # Fallback to common private networks
            networks = ['192.168.1', '192.168.0', '10.0.0', '172.16.0']
        
        return list(set(networks))
    
    def check_activitywatch_instance(self, host: str, port: int) -> Optional[Dict]:
        """Check if ActivityWatch is running on specific host:port"""
        try:
            url = f"http://{host}:{port}/api/0/info"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                info = response.json()
                
                # Get additional info from buckets
                buckets_response = requests.get(f"http://{host}:{port}/api/0/buckets", timeout=self.timeout)
                buckets = buckets_response.json() if buckets_response.status_code == 200 else {}
                
                # Extract hostname from buckets or info
                hostname = self.extract_hostname_from_buckets(buckets) or host
                
                return {
                    "id": f"{hostname}_{port}",
                    "name": hostname,
                    "host": host,
                    "port": port,
                    "version": info.get("version", "unknown"),
                    "hostname": info.get("hostname", hostname),
                    "device_id": info.get("device_id", f"{hostname}_{port}"),
                    "buckets": list(buckets.keys()),
                    "bucket_count": len(buckets),
                    "description": f"ActivityWatch on {hostname}",
                    "discovered_at": datetime.now().isoformat(),
                    "status": "online"
                }
        except Exception as e:
            logger.debug(f"No ActivityWatch at {host}:{port}: {e}")
            return None
    
    def extract_hostname_from_buckets(self, buckets: Dict) -> Optional[str]:
        """Extract hostname from bucket names"""
        for bucket_name in buckets.keys():
            if '_' in bucket_name:
                # Bucket names usually follow pattern like "aw-watcher-window_HOSTNAME"
                parts = bucket_name.split('_')
                if len(parts) > 1:
                    return parts[-1]
        return None
    
    def scan_network_range(self, network_base: str, ports: List[int] = None) -> List[Dict]:
        """Scan a network range for ActivityWatch instances"""
        if ports is None:
            ports = self.default_ports
            
        discovered = []
        
        def check_host_port(host_port):
            host, port = host_port
            result = self.check_activitywatch_instance(host, port)
            if result:
                return result
            return None
        
        # Generate all host:port combinations
        host_port_combinations = []
        for i in range(1, 255):  # Skip .0 and .255
            host = f"{network_base}.{i}"
            for port in ports:
                host_port_combinations.append((host, port))
        
        # Use ThreadPoolExecutor for concurrent scanning
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_host_port = {
                executor.submit(check_host_port, hp): hp 
                for hp in host_port_combinations
            }
            
            for future in as_completed(future_to_host_port):
                result = future.result()
                if result:
                    discovered.append(result)
                    logger.info(f"Discovered ActivityWatch: {result['name']} at {result['host']}:{result['port']}")
        
        return discovered
    
    def discover_local_instances(self) -> List[Dict]:
        """Discover ActivityWatch instances on localhost"""
        discovered = []
        
        # Check common localhost addresses
        localhost_addresses = ['127.0.0.1', 'localhost', '0.0.0.0']
        
        for host in localhost_addresses:
            for port in self.default_ports:
                result = self.check_activitywatch_instance(host, port)
                if result:
                    # Ensure localhost instances have proper hostname
                    if result['name'] in ['127.0.0.1', 'localhost', '0.0.0.0']:
                        result['name'] = socket.gethostname()
                        result['hostname'] = socket.gethostname()
                        result['id'] = f"{socket.gethostname()}_{port}"
                    discovered.append(result)
                    break  # Found one on this host, move to next
        
        return discovered
    
    def discover_from_database(self) -> List[Dict]:
        """Discover developers from database activity records"""
        if not self.db_session:
            return []
        
        try:
            from sqlalchemy import text
            
            # Query unique developers from activity records
            query = text("""
                SELECT DISTINCT 
                    developer_id,
                    developer_name,
                    MAX(created_at) as last_seen,
                    COUNT(*) as activity_count
                FROM activity_records 
                WHERE developer_id IS NOT NULL 
                    AND created_at > :last_month
                GROUP BY developer_id, developer_name
                ORDER BY last_seen DESC
            """)
            
            last_month = datetime.now() - timedelta(days=30)
            result = self.db_session.execute(query, {"last_month": last_month})
            
            db_developers = []
            for row in result:
                db_developers.append({
                    "id": row.developer_id,
                    "name": row.developer_name or row.developer_id,
                    "host": "unknown",  # Will be resolved later
                    "port": 5600,  # Default port
                    "hostname": row.developer_name or row.developer_id,
                    "device_id": row.developer_id,
                    "description": f"From database records ({row.activity_count} activities)",
                    "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                    "activity_count": row.activity_count,
                    "source": "database",
                    "status": "unknown"
                })
            
            return db_developers
            
        except Exception as e:
            logger.error(f"Error discovering from database: {e}")
            return []
    
    def discover_all_developers(self, scan_network: bool = True, scan_local: bool = True, 
                              scan_database: bool = True) -> List[Dict]:
        """Discover all available developers from all sources"""
        all_developers = []
        
        # 1. Discover local instances
        if scan_local:
            logger.info("Discovering local ActivityWatch instances...")
            local_devs = self.discover_local_instances()
            all_developers.extend(local_devs)
            logger.info(f"Found {len(local_devs)} local instances")
        
        # 2. Discover from database
        if scan_database:
            logger.info("Discovering developers from database...")
            db_devs = self.discover_from_database()
            all_developers.extend(db_devs)
            logger.info(f"Found {len(db_devs)} developers in database")
        
        # 3. Scan network (optional, can be slow)
        if scan_network:
            logger.info("Scanning network for ActivityWatch instances...")
            networks = self.get_local_networks()
            
            for network in networks[:2]:  # Limit to first 2 networks to avoid long scans
                logger.info(f"Scanning network {network}.x...")
                network_devs = self.scan_network_range(network)
                all_developers.extend(network_devs)
                logger.info(f"Found {len(network_devs)} instances on {network}.x")
        
        # Remove duplicates based on unique identifier
        unique_developers = {}
        for dev in all_developers:
            # Use device_id or combination of host:port as unique key
            key = dev.get('device_id') or f"{dev['host']}:{dev['port']}"
            if key not in unique_developers:
                unique_developers[key] = dev
            else:
                # Merge information from multiple sources
                existing = unique_developers[key]
                if dev.get('source') == 'database' and not existing.get('activity_count'):
                    existing['activity_count'] = dev.get('activity_count', 0)
                    existing['last_seen'] = dev.get('last_seen')
        
        self.discovered_developers = list(unique_developers.values())
        logger.info(f"Total unique developers discovered: {len(self.discovered_developers)}")
        
        return self.discovered_developers
    
    def refresh_developer_status(self, developers: List[Dict]) -> List[Dict]:
        """Refresh online status for all developers"""
        def check_status(dev):
            if dev.get('source') == 'database' and dev.get('host') == 'unknown':
                dev['status'] = 'database_only'
                return dev
            
            result = self.check_activitywatch_instance(dev['host'], dev['port'])
            dev['status'] = 'online' if result else 'offline'
            dev['last_checked'] = datetime.now().isoformat()
            return dev
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_developers = list(executor.map(check_status, developers))
        
        return updated_developers

# 2. Create activity_watch_client.py - Dynamic client

import requests
from datetime import datetime
from typing import List, Dict, Optional
from developer_discovery import DeveloperDiscovery

class DynamicActivityWatchClient:
    """ActivityWatch client that works with dynamically discovered developers"""
    
    def __init__(self, developer_info: Dict):
        self.developer_info = developer_info
        self.developer_id = developer_info['id']
        self.host = developer_info['host']
        self.port = developer_info['port']
        self.base_url = f"http://{self.host}:{self.port}"
        self.device_id = developer_info.get('device_id', self.developer_id)
        
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
            response = requests.get(f"{self.base_url}/api/0/buckets/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting buckets: {e}")
            return {}
    
    def get_events(self, bucket_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events from a specific bucket"""
        try:
            params = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            response = requests.get(f"{self.base_url}/api/0/buckets/{bucket_id}/events", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting events from {bucket_id}: {e}")
            return []
    
    def get_activity_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get processed activity data"""
        try:
            buckets = self.get_buckets()
            window_buckets = [name for name in buckets.keys() if 'window' in name.lower()]
            
            activities = []
            for bucket_name in window_buckets:
                events = self.get_events(bucket_name, start_time, end_time)
                
                for event in events:
                    data = event.get('data', {})
                    activities.append({
                        'developer_id': self.developer_id,
                        'developer_name': self.developer_info['name'],
                        'developer_hostname': self.developer_info['hostname'],
                        'application_name': data.get('app', data.get('application', 'Unknown')),
                        'window_title': data.get('title', ''),
                        'duration': event.get('duration', 0),
                        'timestamp': event.get('timestamp', ''),
                        'category': self._categorize_activity(data.get('app', '')),
                        'detailed_activity': self._get_detailed_activity(data),
                        'url': data.get('url', ''),
                        'file_path': self._extract_file_path(data.get('title', '')),
                        'bucket_name': bucket_name,
                        'device_id': self.device_id
                    })
            
            return sorted(activities, key=lambda x: x['duration'], reverse=True)
        
        except Exception as e:
            print(f"Error getting activity data: {e}")
            return []
    
    def _categorize_activity(self, app_name: str) -> str:
        """Categorize activity based on application name"""
        app_lower = app_name.lower()
        
        if any(ide in app_lower for ide in ['cursor', 'code', 'vim', 'sublime', 'atom', 'intellij', 'pycharm']):
            return 'Development'
        elif any(browser in app_lower for browser in ['chrome', 'firefox', 'safari', 'edge']):
            return 'Web Browsing'
        elif any(comm in app_lower for comm in ['slack', 'discord', 'teams', 'zoom']):
            return 'Communication'
        else:
            return 'Other'
    
    def _get_detailed_activity(self, data: Dict) -> str:
        """Get detailed activity description"""
        title = data.get('title', '')
        app = data.get('app', '')
        
        if 'cursor' in app.lower() or 'code' in app.lower():
            if any(ext in title.lower() for ext in ['.py', '.js', '.html', '.css', '.json']):
                return f"Coding: {title}"
        elif any(browser in app.lower() for browser in ['chrome', 'firefox', 'safari']):
            if data.get('url'):
                return f"Browsing: {data['url']}"
        
        return title
    
    def _extract_file_path(self, title: str) -> str:
        """Extract file path from window title if available"""
        if any(ext in title.lower() for ext in ['.py', '.js', '.html', '.css', '.json', '.md']):
            parts = title.split(' - ')
            if len(parts) > 1:
                return parts[0]
        return ''

# 3. Enhanced models.py - Add developer tracking

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ActivityRecord(Base):
    __tablename__ = 'activity_records'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    
    # Developer identification (dynamic)
    developer_id = Column(String(255), index=True)
    developer_name = Column(String(255), index=True)
    developer_hostname = Column(String(255))
    device_id = Column(String(255), index=True)
    
    # Activity data
    application_name = Column(String(255), index=True)
    window_title = Column(Text)
    duration = Column(Float)
    category = Column(String(100), index=True)
    detailed_activity = Column(Text)
    url = Column(Text)
    file_path = Column(String(500))
    bucket_name = Column(String(255))
    
    # Timestamps
    activity_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class DiscoveredDeveloper(Base):
    """Cache discovered developers to avoid repeated network scans"""
    __tablename__ = 'discovered_developers'
    
    id = Column(String(255), primary_key=True)  # developer_id
    name = Column(String(255))
    host = Column(String(255))
    port = Column(Integer)
    hostname = Column(String(255))
    device_id = Column(String(255))
    description = Column(Text)
    version = Column(String(50))
    bucket_count = Column(Integer, default=0)
    activity_count = Column(Integer, default=0)
    
    # Status tracking
    status = Column(String(50), default='unknown')  # online, offline, database_only
    last_seen = Column(DateTime)
    last_checked = Column(DateTime)
    
    # Discovery metadata
    source = Column(String(50))  # network, local, database
    discovered_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())