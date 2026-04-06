# fixed_sync_endpoint.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from database import get_db
from activity_categorizer import ActivityCategorizer

router = APIRouter()

@router.post("/api/sync")
async def receive_sync_data(sync_data: dict, db: Session = Depends(get_db)):
    """Sync endpoint with duplicate prevention and Unknown/Untitled filtering"""
    try:
        token = sync_data.get("token")
        data = sync_data.get("data", [])
        timestamp = sync_data.get("timestamp")

        # Validate developer
        developer = db.execute(
            text("SELECT developer_id FROM developers WHERE api_token = :token"),
            {"token": token}
        ).fetchone()
        if not developer:
            return {"error": "Invalid token"}
        developer_id = developer[0]

        categorizer = ActivityCategorizer()
        saved_count = 0
        failed_count = 0
        skipped_duplicates = 0
        skipped_unknown = 0
        saved_afk = 0
        last_ftp_project = None  # Track active FileZilla/FTP project context

        # Process dedicated AFK data from sync payload (if provided)
        afk_data = sync_data.get("afk_data", [])
        for afk_event in afk_data:
            try:
                afk_status = afk_event.get("status", "")
                afk_duration = afk_event.get("duration", 0)
                afk_ts_str = afk_event.get("timestamp", "")
                if not afk_status or afk_duration < 1 or not afk_ts_str:
                    continue
                if isinstance(afk_ts_str, str):
                    afk_ts = datetime.fromisoformat(afk_ts_str.replace('Z', '+00:00'))
                else:
                    afk_ts = afk_ts_str
                db.execute(text("""
                    INSERT INTO afk_records (developer_id, status, duration, timestamp, created_at)
                    VALUES (:developer_id, :status, :duration, :timestamp, :created_at)
                    ON CONFLICT (developer_id, timestamp, duration) DO NOTHING
                """), {
                    "developer_id": developer_id,
                    "status": afk_status,
                    "duration": float(afk_duration),
                    "timestamp": afk_ts,
                    "created_at": datetime.now(timezone.utc)
                })
                db.flush()
                saved_afk += 1
            except IntegrityError:
                db.rollback()
            except Exception as e:
                print(f"Error saving AFK event: {e}")

        for event in data:
            try:
                event_data = event.get("data", {})
                duration = event.get("duration", 0)
                if duration < 5:  # skip very short activities
                    continue

                event_timestamp = event.get("timestamp", timestamp)
                window_title = event_data.get("title", "")
                app_name = event_data.get("app", event_data.get("application", ""))
                url = event_data.get("url", "")
                file_path = event_data.get("file", "")
                vscode_project = event_data.get("project", "")

                # Parse timestamp early (needed for AFK insert too)
                if isinstance(event_timestamp, str):
                    parsed_ts = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                else:
                    parsed_ts = event_timestamp

                # Real AFK watcher event: has data.status field ("afk" or "not-afk")
                afk_status = event_data.get("status")
                if afk_status in ("afk", "not-afk"):
                    try:
                        db.execute(text("""
                            INSERT INTO afk_records (developer_id, status, duration, timestamp, created_at)
                            VALUES (:developer_id, :status, :duration, :timestamp, :created_at)
                            ON CONFLICT (developer_id, timestamp, duration) DO NOTHING
                        """), {
                            "developer_id": developer_id,
                            "status": afk_status,
                            "duration": float(duration),
                            "timestamp": parsed_ts,
                            "created_at": datetime.now(timezone.utc)
                        })
                        db.flush()
                        saved_afk += 1
                    except IntegrityError:
                        db.rollback()
                    continue

                # Unknown/empty app → skip (not a real activity)
                if not app_name or app_name.lower() in ('unknown', ''):
                    if vscode_project or file_path:
                        app_name = "Visual Studio Code"
                    else:
                        skipped_unknown += 1
                        continue

                # Untitled/blank/system windows → skip
                skip_titles = ['untitled', 'unknown', '', 'blank',
                               'program manager', 'task switching', 'task view',
                               'windows default lock screen', 'new tab']
                if not window_title or window_title.lower().strip() in skip_titles:
                    skipped_unknown += 1
                    continue

                # Track FileZilla/FTP project context from window titles
                ftp_project = extract_ftp_project(window_title, app_name)
                if ftp_project:
                    last_ftp_project = ftp_project

                # Extract project name from ORIGINAL title (before cleaning)
                project_name = extract_project_name(window_title, app_name)

                # If VS Code watcher provided a project path, extract folder name from it
                if vscode_project and project_name in ("general", "Unknown", ""):
                    # VS Code project comes as path like "/e:/projects/sinoglobal_mail"
                    clean_project = vscode_project.replace("\\", "/").rstrip("/")
                    folder_name = clean_project.split("/")[-1] if "/" in clean_project else clean_project
                    if folder_name and folder_name.lower() not in ("unknown", "") and len(folder_name) >= 2:
                        project_name = folder_name

                # Fallback: extract project from file_path when VS Code didn't send project
                # e.g. "e:/projects/timesheet/backend/main.py" → "timesheet"
                if project_name in ("general", "Unknown", "") and file_path:
                    clean_fp = file_path.replace("\\", "/").rstrip("/")
                    parts = clean_fp.split("/")
                    # Find the project folder (parent of typical code folders like src, backend, frontend, etc.)
                    code_folders = {'src', 'backend', 'frontend', 'app', 'lib', 'public',
                                    'server', 'client', 'api', 'dist', 'build', 'node_modules',
                                    'vendor', 'packages', 'config', 'tests', 'test', 'scripts'}
                    found_project = None
                    for i, part in enumerate(parts):
                        if part.lower() in code_folders and i > 0:
                            found_project = parts[i - 1]
                            break
                    # If no code folder found, use the parent folder of the file
                    if not found_project and len(parts) >= 3:
                        # Skip drive letter (e:) and take the deepest meaningful folder
                        # e.g. "e:/projects/myapp/index.js" → "myapp"
                        found_project = parts[-2]
                    if found_project and found_project.lower() not in ("unknown", "", "users", "home", "documents", "downloads", "desktop") and len(found_project) >= 2:
                        project_name = found_project

                # If VS Code/IDE returns "general", use FileZilla context
                if project_name == "general" and last_ftp_project:
                    app_lower = app_name.lower()
                    is_ide = any(ide in app_lower for ide in ['code', 'cursor', 'vscode', 'sublime', 'notepad++', 'atom'])
                    if is_ide:
                        project_name = last_ftp_project
                        print(f"  -> Used FTP context: '{last_ftp_project}' for '{window_title[:40]}'...")

                # Clean window title for display/categorization
                for suffix in [" - Google Chrome", " - Mozilla Firefox", " - Microsoft Edge", " - Visual Studio Code"]:
                    window_title = window_title.replace(suffix, "")

                category_info = categorizer.get_detailed_category(window_title, app_name)
                print(f"DEBUG: '{window_title[:50]}' -> project: '{project_name}' | {category_info}")

                # Make sure it always returns valid data
                if not category_info or not category_info.get("category"):
                    category_info = {
                        "category": "browser" if "chrome" in app_name.lower() else "uncategorized",
                        "subcategory": "general"
                    }

                # Insert activity record with duplicate prevention
                insert_query = text("""
                    INSERT INTO activity_records (
                        developer_id, application_name, window_title,
                        url, file_path, duration, timestamp,
                        category, project_name, project_type,
                        created_at
                    ) VALUES (
                        :developer_id, :application_name, :window_title,
                        :url, :file_path, :duration, :timestamp,
                        :category, :project_name, :project_type,
                        :created_at
                    )
                """)

                try:
                    db.execute(insert_query, {
                        "developer_id": developer_id,
                        "application_name": app_name[:255],
                        "window_title": window_title[:500],
                        "url": url[:1000] if url else "",
                        "file_path": file_path[:1000] if file_path else "",
                        "duration": int(duration),
                        "timestamp": parsed_ts,
                        "category": category_info["category"],
                        "project_name": project_name,
                        "project_type": category_info["subcategory"],
                        "created_at": datetime.now(timezone.utc)
                    })
                    db.flush()
                    saved_count += 1
                except IntegrityError:
                    db.rollback()
                    skipped_duplicates += 1
                    continue

            except Exception as e:
                failed_count += 1
                print(f"Error processing event: {e}")
                continue

        db.commit()
        print(f"Synced {saved_count} activities for {developer_id} (afk: {saved_afk}, dupes: {skipped_duplicates}, unknown: {skipped_unknown}, failed: {failed_count})")
        return {
            "success": True,
            "received": len(data),
            "saved": saved_count,
            "afk_saved": saved_afk,
            "duplicates_skipped": skipped_duplicates,
            "unknown_skipped": skipped_unknown,
            "failed": failed_count,
            "developer": developer_id
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Sync error: {e}")
        return {"error": str(e), "success": False}

# Project name extraction function
def extract_project_name(window_title: str, app_name: str) -> str:
    import re
    app_lower = app_name.lower()

    # IDE detection: VS Code, Cursor, Code.exe, etc.
    is_ide = any(ide in app_lower for ide in ['code', 'cursor', 'vscode', 'pycharm', 'intellij', 'webstorm', 'sublime', 'atom'])

    # Pattern 1: "filename - projectname - Visual Studio Code/Cursor/Code"
    vscode_match = re.search(r' - ([^-]+) - (?:Visual Studio Code|VS Code|Cursor|Code)$', window_title)
    if vscode_match:
        return vscode_match.group(1).strip()

    # Pattern 2: "[Claude Code] projectname\file" or similar tool prefixes
    claude_match = re.search(r'\[Claude Code\]\s*([^\\\/]+)', window_title)
    if claude_match:
        return claude_match.group(1).strip()

    # Pattern 3: JetBrains IDEs use em-dash: "projectname – filename"
    jetbrains_match = re.search(r'^([^–]+) – ', window_title)
    if jetbrains_match and any(ide in app_lower for ide in ['intellij', 'pycharm', 'webstorm']):
        return jetbrains_match.group(1).strip()

    # Pattern 4: For IDE apps, try splitting by " - " and taking the folder/project part
    if is_ide:
        parts = [p.strip() for p in window_title.split(' - ')
                 if p.strip() and not re.match(r'^(Visual Studio Code|VS Code|Cursor|Code)$', p.strip(), re.I)]
        # If 2+ parts remain: first is filename, last is project name
        if len(parts) >= 2:
            return parts[-1]
        # Single part that looks like a path: extract parent folder
        if len(parts) == 1:
            path_match = re.search(r'[\\\/]([^\\\/]+)[\\\/][^\\\/]+\.[a-zA-Z0-9]+$', parts[0])
            if path_match:
                return path_match.group(1)

    # Pattern 5: Git path in title
    git_match = re.search(r'[\\\/]([^\\\/]+)[\\\/]\.git', window_title)
    if git_match:
        return git_match.group(1)

    # Pattern 6: GitHub repo URL
    repo_match = re.search(r'github\.com/[^/]+/([^/\s]+)', window_title)
    if repo_match:
        return repo_match.group(1)

    # Pattern 7: File path with parent folder
    folder_match = re.search(r'[\\\/]([^\\\/]+)[\\\/][^\\\/]+\.[a-zA-Z0-9]+$', window_title)
    if folder_match:
        return folder_match.group(1)

    # Pattern 8: Browser tabs - extract meaningful project name
    is_browser = any(b in app_lower for b in ['chrome', 'firefox', 'edge', 'brave', 'opera', 'safari'])
    if is_browser:
        # Remove browser suffix dynamically (last " - BrowserName" pattern)
        clean = re.sub(r'\s*-\s*\S+\s*$', '', window_title).strip() if ' - ' in window_title else window_title.strip()

        # "Database: dbname - tool" -> "dbname"
        db_match = re.match(r'Database:\s*(\S+)', clean)
        if db_match:
            return db_match.group(1)

        # Extract domain from URLs in title, use subdomain as project
        domain_match = re.search(r'https?://([a-zA-Z0-9.-]+)', clean)
        if domain_match:
            domain = domain_match.group(1)
            parts = domain.split('.')
            # 3+ part domain: use subdomain (first part) as project name
            if len(parts) >= 3:
                return parts[0]
            # 2 part domain: use domain name
            if len(parts) >= 2:
                return parts[0]

        # "Page Title | Site Name" -> "Site Name"
        if ' | ' in clean:
            site = clean.split(' | ')[-1].strip()
            if 3 < len(site) < 50:
                return site

        # "Page Title - Site Name" -> "Site Name"
        if ' - ' in clean:
            site = clean.split(' - ')[-1].strip()
            if 3 < len(site) < 40:
                return site

    return "general"


def extract_ftp_project(window_title: str, app_name: str) -> str:
    """
    Extract project/domain from FileZilla/WinSCP window titles.

    FileZilla title formats:
      - "user@domain.com - /remote/path/ - FileZilla"
      - "domain.com - /public_html/projectname/ - FileZilla"
      - "New Site - domain.com - FileZilla"
      - "/remote/path/projectname/ - domain.com - FileZilla"

    WinSCP title formats:
      - "user@domain.com - WinSCP"
      - "/remote/path/ - user@domain.com - WinSCP"

    Returns project name (domain or path-based) or None if not an FTP app.
    """
    import re
    app_lower = app_name.lower()

    if not any(ftp in app_lower for ftp in ['filezilla', 'winscp', 'ftp']):
        return None

    title = window_title.strip()
    if not title:
        return None

    # Extract domain name (e.g., clientdomain.com, 192.168.1.1)
    domain_match = re.search(
        r'(?:@)?([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.(?:com|in|net|org|co\.\w+|io|dev|info|biz|us|uk|edu|gov|[a-z]{2,}))',
        title
    )

    # Also try to extract a meaningful path like /public_html/projectname/
    path_match = re.search(r'/(?:public_html|www|htdocs|var/www/html|home/\w+)/([^/\s]+)', title)

    if path_match and domain_match:
        # Both found: use "domain.com/projectfolder"
        return f"{domain_match.group(1)}/{path_match.group(1)}"
    elif path_match:
        return path_match.group(1)
    elif domain_match:
        return domain_match.group(1)

    # Fallback: try IP address
    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', title)
    if ip_match:
        return f"FTP: {ip_match.group(1)}"

    return None
