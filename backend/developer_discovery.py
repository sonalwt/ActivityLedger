# developer_discovery.py - Simplified version without netifaces dependency

import requests
import socket
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

logger = logging.getLogger(__name__)

class DeveloperDiscovery:
    """Automatically discover ActivityWatch instances on network and local machine"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.discovered_developers = []
        self.default_ports = [5600, 5601, 5602, 5603, 5700]  # Common AW ports
        self.timeout = 3  # Connection timeout in seconds
        
    def get_local_networks(self) -> List[str]:
        """Get local network ranges to scan (simplified version)"""
        networks = []
        try:
            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Extract network base from local IP
            if local_ip and not local_ip.startswith('127.'):
                base_ip = '.'.join(local_ip.split('.')[:-1])
                networks.append(base_ip)
                
            # Add common private network ranges as fallback
            common_networks = ['192.168.1', '192.168.0', '10.0.0', '172.16.0']
            for network in common_networks:
                if network not in networks:
                    networks.append(network)
                    
        except Exception as e:
            logger.warning(f"Could not determine local networks: {e}")
            # Fallback to common private networks
            networks = ['192.168.1', '192.168.0', '10.0.0', '172.16.0']
        
        return networks[:3]  # Limit to 3 networks to avoid long scans
    
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
                hostname = self.extract_hostname_from_buckets(buckets) or info.get("hostname", host)
                
                return {
                    "id": f"{hostname}_{port}",
                    "name": hostname,
                    "host": host,
                    "port": port,
                    "version": info.get("version", "unknown"),
                    "hostname": hostname,
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
        
        # Generate all host:port combinations (limited range for performance)
        host_port_combinations = []
        for i in range(1, 50):  # Scan only first 50 IPs instead of 254 for speed
            host = f"{network_base}.{i}"
            for port in ports:
                host_port_combinations.append((host, port))
        
        # Use ThreadPoolExecutor for concurrent scanning
        with ThreadPoolExecutor(max_workers=30) as executor:  # Reduced workers
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
        localhost_addresses = ['127.0.0.1', 'localhost']
        
        for host in localhost_addresses:
            for port in self.default_ports:
                result = self.check_activitywatch_instance(host, port)
                if result:
                    # Ensure localhost instances have proper hostname
                    if result['name'] in ['127.0.0.1', 'localhost']:
                        try:
                            result['name'] = socket.gethostname()
                            result['hostname'] = socket.gethostname()
                            result['id'] = f"{socket.gethostname()}_{port}"
                        except:
                            result['name'] = 'Local Machine'
                            result['hostname'] = 'localhost'
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
            # Only use columns that exist in the table
            query = text("""
                SELECT DISTINCT 
                    developer_id,
                    MAX(created_at) as last_seen,
                    COUNT(*) as activity_count
                FROM activity_records 
                WHERE developer_id IS NOT NULL 
                    AND created_at > :last_month
                GROUP BY developer_id
                ORDER BY last_seen DESC
            """)
            
            last_month = datetime.now() - timedelta(days=30)
            result = self.db_session.execute(query, {"last_month": last_month})
            
            db_developers = []
            for row in result:
                db_developers.append({
                    "id": row.developer_id,
                    "name": row.developer_id,  # Use developer_id as name since we don't have developer_name
                    "host": "unknown",  # Will be resolved later
                    "port": 5600,  # Default port
                    "hostname": row.developer_id,  # Use developer_id as hostname
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
    
    def discover_all_developers(self, scan_network: bool = False, scan_local: bool = True, 
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
            
            for network in networks[:2]:  # Limit to first 2 networks
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
        
        with ThreadPoolExecutor(max_workers=10) as executor:  # Reduced workers
            updated_developers = list(executor.map(check_status, developers))
        
        return updated_developers