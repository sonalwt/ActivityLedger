"""
Script to extract and update project names from window titles
This script analyzes activity records and attempts to extract project names
from window titles and file paths
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = Config.get_database_url()
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Common IDE patterns for project extraction
IDE_PATTERNS = {
    'vscode': [
        r'^(.+?)\s*-\s*(.+?)\s*-\s*Visual Studio Code',  # file - project - VSCode
        r'^(.+?)\s*●?\s*-\s*(.+?)\s*-\s*Visual Studio Code',  # with unsaved indicator
        r'^\[(.+?)\]\s*(.+?)\s*-\s*Visual Studio Code',  # [workspace] file - VSCode
    ],
    'cursor': [
        r'^(.+?)\s*-\s*(.+?)\s*-\s*Cursor',
        r'^(.+?)\s*●?\s*-\s*(.+?)\s*-\s*Cursor',
    ],
    'pycharm': [
        r'^(.+?)\s*–\s*(.+?)\s*\[(.+?)\]',  # file – path [project]
        r'^(.+?)\s*-\s*PyCharm',
    ],
    'intellij': [
        r'^(.+?)\s*–\s*(.+?)\s*\[(.+?)\]',
        r'^(.+?)\s*-\s*IntelliJ IDEA',
    ],
    'sublime': [
        r'^(.+?)\s*-\s*(.+?)\s*-\s*Sublime Text',
        r'^(.+?)\s*•\s*(.+?)\s*-\s*Sublime Text',
    ]
}

# Web browser project patterns
BROWSER_PATTERNS = {
    'github': r'github\.com/([^/]+)/([^/\s]+)',
    'gitlab': r'gitlab\.com/([^/]+)/([^/\s]+)',
    'bitbucket': r'bitbucket\.org/([^/]+)/([^/\s]+)',
    'localhost': r'localhost:\d+',
    'jira': r'([A-Z]{2,10}-\d+)',  # JIRA ticket pattern
}

def extract_project_from_window_title(window_title, application_name):
    """Extract project name from window title based on application"""
    if not window_title:
        return None
    
    app_lower = application_name.lower() if application_name else ""
    
    # Try IDE patterns
    for ide, patterns in IDE_PATTERNS.items():
        if ide in app_lower:
            for pattern in patterns:
                match = re.search(pattern, window_title)
                if match:
                    # Different IDEs have project name in different positions
                    if ide in ['pycharm', 'intellij'] and len(match.groups()) >= 3:
                        return match.group(3).strip()  # Project is in brackets
                    elif len(match.groups()) >= 2:
                        return match.group(2).strip()  # Project is second group
                    elif len(match.groups()) >= 1:
                        return match.group(1).strip()  # Fallback to first group
    
    # Try browser patterns if it's a browser
    if any(browser in app_lower for browser in ['chrome', 'firefox', 'edge', 'safari', 'brave']):
        for service, pattern in BROWSER_PATTERNS.items():
            match = re.search(pattern, window_title, re.IGNORECASE)
            if match:
                if service in ['github', 'gitlab', 'bitbucket']:
                    return match.group(2)  # Repository name
                elif service == 'jira':
                    return f"JIRA-{match.group(1)}"
                elif service == 'localhost':
                    return "Local Development"
    
    return None

def extract_project_from_file_path(file_path):
    """Extract project name from file path"""
    if not file_path:
        return None
    
    # Common project root indicators
    project_indicators = [
        r'/([^/]+)/src/',
        r'/([^/]+)/app/',
        r'/([^/]+)/lib/',
        r'/([^/]+)/backend/',
        r'/([^/]+)/frontend/',
        r'/([^/]+)/client/',
        r'/([^/]+)/server/',
        r'\\([^\\]+)\\src\\',
        r'\\([^\\]+)\\app\\',
        r'\\([^\\]+)\\backend\\',
        r'\\([^\\]+)\\frontend\\',
    ]
    
    for pattern in project_indicators:
        match = re.search(pattern, file_path, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Try to get the parent folder of common files
    common_files = ['package.json', 'pom.xml', 'build.gradle', 'requirements.txt', 'setup.py']
    for file in common_files:
        if file in file_path.lower():
            parts = file_path.replace('\\', '/').split('/')
            for i, part in enumerate(parts):
                if part.lower() == file and i > 0:
                    return parts[i-1]
    
    return None

def categorize_project(project_name, window_title, application_name):
    """Categorize the project based on context"""
    if not project_name:
        return "Other", "General"
    
    project_lower = project_name.lower()
    app_lower = application_name.lower() if application_name else ""
    title_lower = window_title.lower() if window_title else ""
    
    # Development categories
    if any(ide in app_lower for ide in ['vscode', 'cursor', 'pycharm', 'intellij', 'sublime']):
        if 'backend' in project_lower or 'api' in project_lower or 'server' in project_lower:
            return "Development", "Backend"
        elif 'frontend' in project_lower or 'client' in project_lower or 'web' in project_lower:
            return "Development", "Frontend"
        elif 'mobile' in project_lower or 'app' in project_lower:
            return "Development", "Mobile"
        else:
            return "Development", "General"
    
    # Database work
    if any(db in app_lower for db in ['datagrip', 'pgadmin', 'mysql', 'mongodb']):
        return "Database", "Administration"
    
    # Server management
    if any(server in app_lower or server in title_lower 
           for server in ['plesk', 'cpanel', 'ssh', 'putty', 'filezilla']):
        return "Server Management", "Administration"
    
    # Documentation
    if any(doc in app_lower for doc in ['word', 'docs', 'notion', 'confluence']):
        return "Documentation", "Writing"
    
    # Communication
    if any(comm in app_lower for comm in ['teams', 'slack', 'zoom', 'meet']):
        return "Communication", "Meeting"
    
    return "Work", "General"

def update_project_info():
    """Update activity records with extracted project information"""
    with SessionLocal() as db:
        try:
            # Get activities without project names
            activities = db.execute(text("""
                SELECT id, window_title, application_name, file_path, url
                FROM activity_records
                WHERE project_name IS NULL
                AND timestamp >= NOW() - INTERVAL '30 days'
                ORDER BY timestamp DESC
                LIMIT 5000
            """)).fetchall()
            
            logger.info(f"Found {len(activities)} activities to process")
            
            updated = 0
            projects_found = {}
            
            for activity in activities:
                activity_id, window_title, app_name, file_path, url = activity
                
                # Try to extract project name
                project_name = None
                
                # First try window title
                project_name = extract_project_from_window_title(window_title, app_name)
                
                # If not found, try file path
                if not project_name and file_path:
                    project_name = extract_project_from_file_path(file_path)
                
                # If still not found and it's a browser, check URL
                if not project_name and url and 'browser' in (app_name or '').lower():
                    for service, pattern in BROWSER_PATTERNS.items():
                        match = re.search(pattern, url, re.IGNORECASE)
                        if match:
                            if service in ['github', 'gitlab', 'bitbucket']:
                                project_name = match.group(2)
                                break
                
                # Update if project found
                if project_name:
                    # Clean up project name
                    project_name = project_name.strip()
                    if len(project_name) > 100:
                        project_name = project_name[:100]
                    
                    # Get category
                    project_type, project_category = categorize_project(
                        project_name, window_title, app_name
                    )
                    
                    # Update record
                    db.execute(text("""
                        UPDATE activity_records
                        SET project_name = :project_name,
                            project_type = :project_type
                        WHERE id = :id
                    """), {
                        "project_name": project_name,
                        "project_type": project_type,
                        "id": activity_id
                    })
                    
                    updated += 1
                    
                    # Track projects
                    if project_name not in projects_found:
                        projects_found[project_name] = {
                            'count': 0,
                            'types': set(),
                            'apps': set()
                        }
                    projects_found[project_name]['count'] += 1
                    projects_found[project_name]['types'].add(project_type)
                    if app_name:
                        projects_found[project_name]['apps'].add(app_name)
                    
                    if updated % 100 == 0:
                        db.commit()
                        logger.info(f"Updated {updated} records...")
            
            db.commit()
            
            logger.info(f"\n=== PROJECT EXTRACTION COMPLETE ===")
            logger.info(f"Total activities processed: {len(activities)}")
            logger.info(f"Activities with projects found: {updated}")
            logger.info(f"Unique projects found: {len(projects_found)}")
            
            if projects_found:
                logger.info("\n=== TOP PROJECTS ===")
                sorted_projects = sorted(
                    projects_found.items(), 
                    key=lambda x: x[1]['count'], 
                    reverse=True
                )[:20]
                
                for project, info in sorted_projects:
                    logger.info(f"\n{project}:")
                    logger.info(f"  Activities: {info['count']}")
                    logger.info(f"  Types: {', '.join(info['types'])}")
                    logger.info(f"  Apps: {', '.join(list(info['apps'])[:3])}")
            
        except Exception as e:
            logger.error(f"Error updating project info: {e}")
            db.rollback()
            raise

def get_project_statistics():
    """Get statistics about projects in the database"""
    with SessionLocal() as db:
        # Overall stats
        stats = db.execute(text("""
            SELECT 
                COUNT(DISTINCT project_name) as unique_projects,
                COUNT(*) as total_activities,
                COUNT(CASE WHEN project_name IS NOT NULL THEN 1 END) as activities_with_projects,
                COUNT(DISTINCT developer_id) as developers
            FROM activity_records
            WHERE timestamp >= NOW() - INTERVAL '30 days'
        """)).fetchone()
        
        logger.info("\n=== PROJECT STATISTICS ===")
        logger.info(f"Unique projects: {stats[0]}")
        logger.info(f"Total activities: {stats[1]}")
        logger.info(f"Activities with projects: {stats[2]} ({stats[2]/stats[1]*100:.1f}%)")
        logger.info(f"Active developers: {stats[3]}")
        
        # Top projects by hours
        top_projects = db.execute(text("""
            SELECT 
                project_name,
                project_type,
                SUM(duration) / 3600.0 as total_hours,
                COUNT(*) as activity_count,
                COUNT(DISTINCT developer_id) as developers
            FROM activity_records
            WHERE project_name IS NOT NULL
            AND timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY project_name, project_type
            ORDER BY total_hours DESC
            LIMIT 15
        """)).fetchall()
        
        logger.info("\n=== TOP PROJECTS BY HOURS ===")
        for project, ptype, hours, activities, devs in top_projects:
            logger.info(f"{project} ({ptype}):")
            logger.info(f"  {hours:.1f} hours, {activities} activities, {devs} developers")

if __name__ == "__main__":
    logger.info("Starting project extraction process...")
    update_project_info()
    get_project_statistics()
