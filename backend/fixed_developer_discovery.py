# backend/fixed_developer_discovery.py
"""
Fixed Developer Discovery that includes developers from the developers table
"""

from developer_discovery import DeveloperDiscovery
import logging
from datetime import datetime, timezone
from sqlalchemy import text

logger = logging.getLogger(__name__)

class FixedDeveloperDiscovery(DeveloperDiscovery):
    """Extended DeveloperDiscovery that also checks the developers table"""
    
    def discover_from_developers_table(self):
        """Get developers from the developers table"""
        if not self.db_session:
            return []
            
        try:
            # Query the developers table
            query = text("""
                SELECT 
                    id,
                    developer_id,
                    name,
                    email,
                    active,
                    api_token,
                    created_at,
                    last_sync
                FROM developers
                WHERE active = true
            """)
            
            result = self.db_session.execute(query)
            
            developers = []
            for row in result:
                # Count activities for this developer
                activity_count = 0
                last_activity = None
                try:
                    count_query = text("""
                        SELECT 
                            COUNT(*) as count,
                            MAX(timestamp) as last_activity
                        FROM activity_records 
                        WHERE developer_id = :dev_id
                    """)
                    count_result = self.db_session.execute(count_query, {
                        "dev_id": row.developer_id
                    }).fetchone()
                    
                    if count_result:
                        activity_count = count_result.count or 0
                        last_activity = count_result.last_activity
                except Exception as e:
                    logger.warning(f"Error counting activities for {row.name}: {e}")
                
                developers.append({
                    "id": row.developer_id or f"dev_{row.id}",
                    "name": row.name,
                    "host": "unknown",
                    "port": 5600,
                    "hostname": row.name,
                    "device_id": row.developer_id or f"dev_{row.id}",
                    "description": f"Registered developer ({activity_count} activities)",
                    "last_seen": last_activity.isoformat() if last_activity else row.created_at.isoformat() if row.created_at else None,
                    "activity_count": activity_count,
                    "source": "developers_table",
                    "status": "registered",
                    "email": row.email,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "version": "N/A",
                    "bucket_count": 0
                })
                
            logger.info(f"Found {len(developers)} developers in developers table")
            return developers
            
        except Exception as e:
            logger.error(f"Error discovering from developers table: {e}")
            return []
    
    def discover_all_developers(self, scan_network: bool = False, scan_local: bool = True, 
                              scan_database: bool = True, include_developers_table: bool = True) -> list:
        """Extended discovery that includes developers table"""
        # Get developers from parent class methods
        all_developers = super().discover_all_developers(scan_network, scan_local, scan_database)
        
        # Add developers from developers table
        if include_developers_table:
            logger.info("Discovering developers from developers table...")
            table_devs = self.discover_from_developers_table()
            
            # Merge with existing developers (avoid duplicates)
            existing_ids = {dev['id'] for dev in all_developers}
            for dev in table_devs:
                if dev['id'] not in existing_ids:
                    all_developers.append(dev)
                else:
                    # Update existing entry with additional info
                    for i, existing in enumerate(all_developers):
                        if existing['id'] == dev['id']:
                            # Merge information
                            if not existing.get('email'):
                                existing['email'] = dev.get('email')
                            if dev.get('activity_count', 0) > existing.get('activity_count', 0):
                                existing['activity_count'] = dev['activity_count']
                            break
        
        logger.info(f"Total developers after including developers table: {len(all_developers)}")
        return all_developers
