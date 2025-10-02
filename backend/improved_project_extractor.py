# improved_project_extractor.py
"""
Improved Project Extractor - Better extraction of project names from window titles
"""
import re
from typing import Dict, Optional

def extract_project_info(activity_data: Dict) -> Dict[str, Optional[str]]:
    """
    Extract project information from activity data with improved logic
    """
    app_name = (activity_data.get("application_name", "") or "").lower()
    window_title = activity_data.get("window_title", "") or ""
    file_path = activity_data.get("file_path", "")
    
    # Skip non-work activities
    if is_non_work_activity(window_title, app_name):
        return {"project_name": None, "project_type": None, "project_file": None}
    
    # Try multiple extraction methods in order of priority
    
    # 1. Extract from window title patterns
    project_info = extract_from_window_title(window_title, app_name)
    if project_info.get("project_name"):
        return project_info
    
    # 2. Extract from file path
    if file_path:
        project_info = extract_from_file_path(file_path)
        if project_info.get("project_name"):
            return project_info
    
    # 3. Extract from application-specific patterns
    project_info = extract_from_app_patterns(window_title, app_name)
    if project_info.get("project_name"):
        return project_info
    
    # 4. Fallback to generic extraction
    return extract_generic_project(window_title, app_name)

def is_non_work_activity(window_title: str, app_name: str) -> bool:
    """Check if activity is non-work related"""
    combined = f"{window_title} {app_name}".lower()
    
    non_work_patterns = [
        "lock screen", "locked", "lockapp", "logonui",
        "youtube", "netflix", "spotify", "twitch", "disney",
        "hulu", "prime video", "music", "video", "movie",
        "game", "steam", "epic games", "origin", "battle.net"
    ]
    
    return any(pattern in combined for pattern in non_work_patterns)

def extract_from_window_title(window_title: str, app_name: str) -> Dict[str, Optional[str]]:
    """Extract project from common window title patterns"""
    
    # Pattern 1: "project_name - Application" (e.g., "timesheet_new - Cursor")
    match = re.match(r'^([^-]+?)\s*-\s*(.+)$', window_title)
    if match:
        project_part = match.group(1).strip()
        app_part = match.group(2).strip()
        
        # Check if it's a meaningful project name
        if len(project_part) > 2 and not project_part.lower() in ['new tab', 'untitled', 'new file']:
            # Determine project type based on app
            project_type = determine_project_type(app_part, app_name)
            
            # Clean up the project name
            project_name = clean_project_name(project_part)
            
            return {
                "project_name": project_name,
                "project_type": project_type,
                "project_file": app_part
            }
    
    # Pattern 2: IDEs with "file - project - IDE" pattern
    ide_pattern = r'^(.+?)\s*-\s*(.+?)\s*-\s*(Visual Studio Code|Cursor|Code|PyCharm|IntelliJ|Sublime|Atom|VS Code)'
    ide_match = re.search(ide_pattern, window_title, re.I)
    if ide_match:
        file_name = ide_match.group(1).strip()
        project_name = clean_project_name(ide_match.group(2).strip())
        return {
            "project_name": project_name,
            "project_type": "Development",
            "project_file": file_name
        }
    
    # Pattern 3: Terminal/Server connections (e.g., "Termius - Node Server")
    if "termius" in app_name.lower() or "terminal" in app_name.lower():
        parts = window_title.split(' - ')
        if len(parts) >= 2:
            server_name = parts[-1].strip()
            return {
                "project_name": f"Server: {server_name}",
                "project_type": "Server Management",
                "project_file": "Terminal Session"
            }
    
    return {}

def extract_from_file_path(file_path: str) -> Dict[str, Optional[str]]:
    """Extract project from file path"""
    if not file_path:
        return {}
    
    # Normalize path separators
    path_parts = file_path.replace('\\', '/').split('/')
    
    # Look for common project indicators
    for i, part in enumerate(path_parts):
        if part.lower() in ['projects', 'repos', 'workspace', 'src', 'documents']:
            if i + 1 < len(path_parts):
                project_name = clean_project_name(path_parts[i + 1])
                return {
                    "project_name": project_name,
                    "project_type": "Development",
                    "project_file": path_parts[-1] if path_parts else "File"
                }
    
    # Use parent directory as project
    if len(path_parts) >= 2:
        project_name = clean_project_name(path_parts[-2])
        if project_name and len(project_name) > 2:
            return {
                "project_name": project_name,
                "project_type": "Development",
                "project_file": path_parts[-1]
            }
    
    return {}

def extract_from_app_patterns(window_title: str, app_name: str) -> Dict[str, Optional[str]]:
    """Extract based on specific application patterns"""
    
    # Browser patterns
    if any(browser in app_name for browser in ["chrome", "firefox", "edge", "safari"]):
        # Local development
        if "localhost:" in window_title or "127.0.0.1:" in window_title:
            port_match = re.search(r'(?:localhost|127\.0\.0\.1):(\d+)', window_title)
            port = port_match.group(1) if port_match else "3000"
            
            # Try to extract project name from page title
            title_parts = window_title.split(' - ')
            if len(title_parts) > 1:
                project_name = clean_project_name(title_parts[0])
                if project_name and project_name.lower() not in ['react app', 'vue app', 'localhost']:
                    return {
                        "project_name": project_name,
                        "project_type": "Web Development",
                        "project_file": f"localhost:{port}"
                    }
            
            return {
                "project_name": f"Local Dev:{port}",
                "project_type": "Web Development",
                "project_file": f"localhost:{port}"
            }
        
        # GitHub/GitLab
        if "github.com" in window_title or "gitlab.com" in window_title:
            repo_match = re.search(r'([^/\s]+/[^/\s]+?)(?:\s*[-·]|\s*$)', window_title)
            if repo_match:
                return {
                    "project_name": f"GitHub: {repo_match.group(1)}",
                    "project_type": "Repository",
                    "project_file": "Source Control"
                }
        
        # Extract domain as project
        domain_match = re.search(r'https?://([^/\s]+)|([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', window_title)
        if domain_match:
            domain = domain_match.group(1) or domain_match.group(2)
            return {
                "project_name": f"Web: {domain}",
                "project_type": "Web Browsing",
                "project_file": "Website"
            }
    
    # Database tools
    if any(db in app_name for db in ["mysql", "postgres", "mongodb", "datagrip", "phpmyadmin"]):
        # Extract database name
        db_match = re.search(r'(\w+)(?:\s*@\s*|\.|\s+database)', window_title, re.I)
        if db_match:
            return {
                "project_name": f"DB: {db_match.group(1)}",
                "project_type": "Database",
                "project_file": "Database Management"
            }
    
    # File transfer
    if any(ftp in app_name for ftp in ["filezilla", "winscp", "cyberduck"]):
        # Extract server/domain
        server_match = re.search(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|\d+\.\d+\.\d+\.\d+)', window_title)
        if server_match:
            return {
                "project_name": f"FTP: {server_match.group(1)}",
                "project_type": "File Transfer",
                "project_file": "Remote Server"
            }
    
    return {}

def extract_generic_project(window_title: str, app_name: str) -> Dict[str, Optional[str]]:
    """Generic project extraction as fallback"""
    
    # Clean up window title
    if window_title and len(window_title) > 3:
        # Take first meaningful part
        parts = window_title.split(' - ')
        project_name = clean_project_name(parts[0])
        
        if project_name and len(project_name) > 2:
            return {
                "project_name": project_name,
                "project_type": determine_project_type(window_title, app_name),
                "project_file": "Activity"
            }
    
    # Use application name as last resort
    if app_name and len(app_name) > 3:
        app_clean = app_name.replace('.exe', '').title()
        return {
            "project_name": app_clean,
            "project_type": "Application",
            "project_file": "General"
        }
    
    return {
        "project_name": None,
        "project_type": None,
        "project_file": None
    }

def clean_project_name(name: str) -> str:
    """Clean and standardize project name"""
    if not name:
        return ""
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^\W+|\W+$', '', name)  # Remove leading/trailing non-word chars
    name = re.sub(r'\s+', ' ', name)       # Normalize whitespace
    
    # Remove file extensions
    name = re.sub(r'\.(py|js|html|css|php|java|cpp|c|rb|go|rs)$', '', name, flags=re.I)
    
    # Handle underscore/hyphen separated names
    if '_' in name or '-' in name:
        # Convert to title case
        parts = re.split(r'[_-]', name)
        name = ' '.join(part.capitalize() for part in parts if part)
    
    # Limit length
    if len(name) > 50:
        name = name[:50] + "..."
    
    return name.strip()

def determine_project_type(window_title: str, app_name: str) -> str:
    """Determine project type based on context"""
    combined = f"{window_title} {app_name}".lower()
    
    # Check for specific types
    if any(ide in combined for ide in ["cursor", "vscode", "pycharm", "intellij", "sublime"]):
        return "Development"
    elif any(server in combined for server in ["termius", "ssh", "putty", "rdp"]):
        return "Server Management"
    elif any(db in combined for db in ["mysql", "postgres", "mongodb", "database"]):
        return "Database"
    elif any(web in combined for web in ["localhost", "127.0.0.1", "webpack", "react"]):
        return "Web Development"
    elif any(api in combined for api in ["postman", "insomnia", "api"]):
        return "API Development"
    elif any(design in combined for design in ["figma", "photoshop", "sketch"]):
        return "Design"
    elif any(doc in combined for doc in ["notion", "confluence", "jira", "trello"]):
        return "Documentation"
    else:
        return "General"
