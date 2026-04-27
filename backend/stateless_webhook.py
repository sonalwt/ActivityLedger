from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import json
import hashlib
import os
from pydantic import BaseModel
from database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ActivityWatchEvent(BaseModel):
    timestamp: str
    duration: float
    data: Dict[str, Any]

def validate_stateless_token(developer_id: str, provided_token: str) -> bool:
    """Validate token without database lookup - uses master secret"""
    master_secret = os.getenv("MASTER_SECRET", "your-master-secret-for-token-generation")
    
    # Recreate the expected token using same algorithm as generator
    token_input = f"{developer_id}:{master_secret}:{datetime.now().year}"
    token_hash = hashlib.sha256(token_input.encode()).hexdigest()
    
    # Convert to URL-safe format
    import base64
    token_bytes = bytes.fromhex(token_hash[:48])
    expected_token = base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
    
    return expected_token == provided_token

def categorize_application(app_name: str, window_title: str = "") -> str:
    """Categorize application based on name and window title"""
    if not app_name:
        return 'other'
    
    app_name_lower = app_name.lower()
    window_title_lower = window_title.lower() if window_title else ""
    
    # Browsers
    if any(browser in app_name_lower for browser in ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave', 'dia']):
        return 'browser'
    
    # IDEs and Code Editors (Windows + Mac + Linux)
    if any(ide in app_name_lower for ide in ['vscode', 'visual studio', 'pycharm', 'intellij', 'sublime', 'atom', 'vim', 'nvim', 'neovim', 'macvim', 'emacs', 'notepad++', 'cursor', 'code', 'xcode', 'android studio', 'fleet', 'bbedit', 'textmate', 'nova', 'coteditor']):
        return 'development'
    
    # Database Tools
    if any(db in app_name_lower for db in ['datagrip', 'pgadmin', 'mysql', 'dbeaver', 'navicat', 'sqlserver', 'oracle']):
        return 'database'
    
    # Productivity
    if any(prod in app_name_lower for prod in ['word', 'excel', 'powerpoint', 'outlook', 'teams', 'slack', 'discord', 'zoom', 'notion', 'obsidian', 'postman']):
        return 'productivity'
    
    # Media
    if any(media in app_name_lower for media in ['spotify', 'youtube', 'vlc', 'media player', 'netflix', 'twitch']):
        return 'entertainment'
    
    # System processes (Windows + Mac + Linux)
    if any(system in app_name_lower for system in ['explorer', 'finder', 'terminal', 'iterm', 'cmd', 'powershell', 'task manager', 'activity monitor', 'lock', 'dwm', 'winlogon', 'preview', 'dia', 'nautilus', 'thunar']):
        return 'system'
    
    return 'other'

def _extract_folder_from_filezilla_title(title: str) -> str:
    """
    Extract the actual project folder from a FileZilla window title.
    FileZilla title format: "site_name - /remote/path/to/project/ - FileZilla"
    Returns the first meaningful folder from the remote path, or the site name as fallback.
    """
    parts = title.split(' - ')
    # Common server path directories to skip when looking for the project folder
    skip_dirs = {
        'var', 'www', 'html', 'home', 'usr', 'opt', 'srv', 'root',
        'public_html', 'htdocs', 'webapps', 'sites', 'data', 'etc',
        'tmp', 'log', 'logs', 'lib', 'bin', 'sbin', 'dev', 'proc',
    }

    # Look for a remote path part in the FileZilla title
    for part in parts:
        part = part.strip()
        if part.startswith('/') or (part.count('/') >= 2 and part.lower() != 'filezilla'):
            # This looks like a remote path — extract meaningful project folder
            path_segments = [p for p in part.split('/') if p]
            meaningful = [p for p in path_segments if p.lower() not in skip_dirs]
            if meaningful:
                return meaningful[0]

    # Fallback: return site name (first part) if no path found
    if len(parts) >= 2:
        site_name = parts[0].strip()
        if site_name and site_name.lower() != 'filezilla' and len(site_name) > 2:
            return site_name
    return None


def resolve_ide_project(db, developer_id: str, timestamp, vs_code_project: str = None) -> str:
    """
    When VS Code has no project folder or shows a FileZilla site name,
    check recent FileZilla activity to find the actual project folder from the remote path.

    Args:
        vs_code_project: If provided, only match FileZilla titles containing this site name.
                         This is used to verify if a VS Code project name is actually a FileZilla site.
    """
    try:
        from sqlalchemy import text

        if vs_code_project:
            # Check if VS Code project name matches a FileZilla site name
            fz = db.execute(text("""
                SELECT window_title FROM activity_records
                WHERE developer_id = :dev_id
                  AND LOWER(application_name) LIKE '%filezilla%'
                  AND window_title ILIKE :site_pattern
                  AND timestamp BETWEEN :t0 AND :t1
                ORDER BY timestamp DESC LIMIT 1
            """), {
                "dev_id": developer_id,
                "t0": timestamp - timedelta(minutes=30),
                "t1": timestamp + timedelta(minutes=5),
                "site_pattern": f"%{vs_code_project}%FileZilla%",
            })
        else:
            # General lookup: find any recent FileZilla activity
            fz = db.execute(text("""
                SELECT window_title FROM activity_records
                WHERE developer_id = :dev_id
                  AND LOWER(application_name) LIKE '%filezilla%'
                  AND window_title LIKE '%- %FileZilla%'
                  AND timestamp BETWEEN :t0 AND :t1
                ORDER BY timestamp DESC LIMIT 1
            """), {
                "dev_id": developer_id,
                "t0": timestamp - timedelta(minutes=30),
                "t1": timestamp + timedelta(minutes=5),
            })

        row = fz.fetchone()
        if row and row[0]:
            return _extract_folder_from_filezilla_title(row[0])
        return None
    except Exception:
        return None


def extract_project_info(window_title: str, app_name: str, url: str = None) -> dict:
    """Extract project information from window title, app name, and URL"""
    project_info = {
        'project_name': None,
        'project_type': 'Work',
        'file_path': None,
        'url': url,
        'detailed_activity': None
    }
    
    if not window_title and not app_name:
        return project_info
    
    app_name_lower = app_name.lower() if app_name else ""
    window_title_lower = window_title.lower() if window_title else ""
    
    # IDE Project Detection
    ide_names = ['visual studio code', 'cursor', 'code', 'pycharm', 'intellij', 'sublime text', 'atom', 'xcode', 'android studio', 'fleet', 'bbedit', 'textmate', 'nova', 'coteditor']
    if any(ide in app_name_lower for ide in ['cursor', 'vscode', 'code', 'pycharm', 'intellij', 'xcode', 'android studio', 'fleet', 'sublime', 'bbedit', 'textmate', 'nova', 'coteditor']):
        # Support " | ", " - ", and " — " (em dash, used by Mac) delimiters
        if ' | ' in window_title:
            separator = ' | '
        elif ' \u2014 ' in window_title:
            separator = ' \u2014 '
        elif ' \u2013 ' in window_title:
            separator = ' \u2013 '
        else:
            separator = ' - '
        if separator in window_title:
            parts = window_title.split(separator)
            # Filter out the IDE name from parts
            filtered_parts = [p.strip() for p in parts if p.strip().lower() not in ide_names]

            if len(filtered_parts) >= 2:
                # Pattern: "filename | projectname | Visual Studio Code"
                filename = filtered_parts[0]
                project = filtered_parts[1]

                # If project looks like a filename, swap with filename if it's not
                if '.' in project and not project.startswith('.') and not ('.' in filename and not filename.startswith('.')):
                    project, filename = filename, project

                project_info.update({
                    'project_name': project,
                    'project_type': 'Development',
                    'file_path': f"{project}/{filename}" if '.' in filename else project,
                    'detailed_activity': f"Coding: {filename} in {project}"
                })
                return project_info
            elif len(filtered_parts) == 1:
                part = filtered_parts[0]
                # Check if it's a filename (has extension) or a project folder name
                has_extension = '.' in part and not part.startswith('.')
                if has_extension:
                    # Pattern: "filename.js | Visual Studio Code" (single file, no folder)
                    project_info.update({
                        'project_name': 'IDE Work',
                        'project_type': 'Development',
                        'file_path': part,
                        'detailed_activity': f"Coding: {part}"
                    })
                else:
                    # Pattern: "projectFolder | Visual Studio Code" (folder open, no file tab)
                    # Skip generic/noise folder names — let the recent-activity fallback find the real project
                    _noise_folders = {
                        'src', 'components', 'pages', 'utils', 'hooks', 'services',
                        'models', 'views', 'controllers', 'routes', 'middleware',
                        'helpers', 'config', 'public', 'static', 'assets', 'styles',
                        'data', 'temp', 'tmp', 'test', 'tests', 'build', 'dist',
                        'backend', 'frontend', 'server', 'client', 'app', 'lib',
                        'scripts', 'docs', 'output', 'input', 'logs', 'cache',
                    }
                    if part.lower() in _noise_folders:
                        project_info.update({
                            'project_name': 'IDE Work',
                            'project_type': 'Development',
                            'detailed_activity': f"Development: {part}"
                        })
                    else:
                        project_info.update({
                            'project_name': part,
                            'project_type': 'Development',
                            'file_path': None,
                            'detailed_activity': f"Development: {part}"
                        })
                return project_info

        # No separator in title or empty after filtering — just IDE name
        project_info.update({
            'project_name': 'IDE Work',
            'project_type': 'Development',
            'detailed_activity': f"Development: {window_title}" if window_title else 'IDE Work'
        })
        return project_info
    
    # Browser Project Detection (including Dia browser on Mac)
    elif any(browser in app_name_lower for browser in ['chrome', 'firefox', 'edge', 'safari', 'dia']):
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')

                # Localhost development
                if 'localhost' in domain or '127.0.0.1' in domain:
                    project_info.update({
                        'project_name': f"localhost:{parsed.port or '3000'}",
                        'project_type': 'Web Development',
                        'detailed_activity': f"Local Development: {window_title}"
                    })
                    return project_info

                # Work-related domains
                work_domains = ['github.com', 'stackoverflow.com', 'docs.', 'api.', 'developer.', 'console.']
                if any(work_domain in domain for work_domain in work_domains):
                    project_info.update({
                        'project_name': domain,
                        'project_type': 'Web Research',
                        'detailed_activity': f"Research: {window_title}"
                    })
                    return project_info

            except Exception:
                pass

        # Fallback to window title
        if ' - ' in window_title:
            # Skip blacklisted (non-work) sites using the existing categorizer blacklist
            from activity_categorizer import get_categorizer
            cat, _ = get_categorizer().categorize_activity(window_title, app_name)
            if cat == 'non-work':
                return project_info  # project_name stays None

            # Strip browser/app suffix (e.g. " - Dia", " - Google Chrome")
            import re as _re
            clean = _re.sub(r'\s*-\s*\S+\s*$', '', window_title).strip()

            # Extract GitHub org/repo name — pattern: "CapOrg/repo-name"
            # Matches titles like "PR title — Mahindra-Manulife/mahindra-manulife-retail"
            github_match = _re.search(r'[A-Z][A-Za-z0-9-]*/([A-Za-z][A-Za-z0-9-]+)', clean)
            if github_match:
                repo = github_match.group(1)
                if len(repo) > 3:
                    project_info.update({
                        'project_name': repo,
                        'project_type': 'Development',
                        'detailed_activity': f"GitHub: {clean[:80]}"
                    })
                    return project_info

            # "Page Title | Site Name" -> use site name
            if ' | ' in clean:
                site = clean.split(' | ')[-1].strip()
                if 3 < len(site) < 50:
                    project_info.update({
                        'project_name': site,
                        'project_type': 'Web Browsing',
                        'detailed_activity': f"Browsing: {site}"
                    })
                    return project_info

            page_title = window_title.split(' - ')[0].strip()
            project_info.update({
                'project_name': page_title,
                'project_type': 'Web Browsing',
                'detailed_activity': f"Browsing: {page_title}"
            })
            return project_info
    
    # File Explorer / Finder (Mac) / Nautilus (Linux) - extract project name from path
    if ('explorer' in app_name_lower and ' - file explorer' in window_title_lower) or \
       app_name_lower in ['finder', 'nautilus', 'thunar', 'dolphin', 'nemo']:
        path = window_title.split(' - ')[0].strip()
        # Extract last folder name from path as project name
        import re
        parts = re.split(r'[/\\]', path)
        # Get the deepest folder name (last non-empty part)
        folder_name = None
        for p in reversed(parts):
            if p.strip() and p.strip() not in ['D:', 'C:', 'E:', 'projects', 'repos', 'code', 'www']:
                folder_name = p.strip()
                break
        if folder_name:
            project_info.update({
                'project_name': folder_name,
                'project_type': 'Development',
                'detailed_activity': f"File Explorer: {path}"
            })
            return project_info

    # Default fallback
    clean_app_name = app_name.replace('.exe', '') if app_name else 'Unknown'
    project_info.update({
        'project_name': clean_app_name,
        'project_type': 'Work',
        'detailed_activity': f"{clean_app_name}: {window_title}" if window_title else clean_app_name
    })

    return project_info

@router.post("/activitywatch/webhook")
async def receive_activitywatch_webhook_stateless(
    request: Request,
    developer_id: str = Header(..., alias="Developer-ID"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Receive ActivityWatch data via webhook - stateless token validation"""
    
    # Extract token from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    
    # Validate token using stateless method (no database lookup)
    if not validate_stateless_token(developer_id, token):
        logger.warning(f"Invalid token for developer {developer_id}")
        raise HTTPException(status_code=401, detail="Invalid developer or token")
    
    logger.info(f"Received ActivityWatch webhook from {developer_id}")
    
    try:
        # Get raw JSON data
        webhook_data = await request.json()
        
        processed_activities = 0
        skipped_duplicates = 0

        # Process each bucket
        for bucket_name, bucket_data in webhook_data.items():
            if isinstance(bucket_data, list):

                # AFK watcher bucket: store events in afk_records table
                if 'afk' in bucket_name.lower():
                    from models import AFKRecord
                    for event in bucket_data:
                        if not isinstance(event, dict):
                            continue
                        ts_str = event.get('timestamp')
                        dur = event.get('duration', 0)
                        afk_status = event.get('data', {}).get('status')
                        if not ts_str or dur < 1 or afk_status not in ('afk', 'not-afk'):
                            continue
                        try:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            with db.begin_nested():
                                db.add(AFKRecord(
                                    developer_id=developer_id,
                                    status=afk_status,
                                    duration=float(dur),
                                    timestamp=ts
                                ))
                        except IntegrityError:
                            pass  # Duplicate — savepoint auto-rolled back
                        except Exception as e:
                            logger.error(f"Error processing AFK event: {e}")
                    continue  # Skip to next bucket

                # Process window/app events
                for event in bucket_data:
                    if not isinstance(event, dict):
                        continue

                    # Extract event data
                    timestamp_str = event.get('timestamp')
                    duration = event.get('duration', 0)
                    data = event.get('data', {})

                    if not timestamp_str or duration < 5:  # Skip very short activities
                        continue

                    try:
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        # Extract activity information
                        app_name = data.get('app') or data.get('application', 'Unknown')
                        window_title = data.get('title', '')
                        url = data.get('url', None)
                        aw_project = data.get('project', '')
                        aw_file = data.get('file', '')
                        
                        # Skip if no meaningful data
                        if not app_name or app_name == 'Unknown':
                            continue

                        # Skip untitled/blank/system/idle windows
                        skip_titles = ['untitled', 'unknown', '', 'blank',
                                       'program manager', 'task switching', 'task view',
                                       'windows default lock screen', 'new tab']
                        if not window_title or window_title.lower().strip() in skip_titles:
                            continue

                        # Cap duration for system activities (max 60s per event)
                        system_titles = ['search', 'task manager', 'control panel']
                        if window_title.lower().strip() in system_titles and duration > 60:
                            duration = 60

                        # Categorize and extract project info
                        category = categorize_application(app_name, window_title)
                        project_info = extract_project_info(window_title, app_name, url)

                        # Use ActivityWatch project/file fields if available (e.g., from aw-watcher-vscode)
                        if aw_project and (not project_info['project_name'] or project_info['project_name'] == 'IDE Work'):
                            project_info['project_name'] = aw_project
                            project_info['project_type'] = 'Development'
                        if aw_file and not project_info.get('file_path'):
                            project_info['file_path'] = aw_file

                        # If VS Code has no project, resolve from recent IDE activity or FileZilla
                        if project_info['project_name'] == 'IDE Work' and category == 'development':
                            # Try: recent activity from the same IDE app (e.g. when using Claude Code)
                            from models import ActivityRecord as AR2
                            recent_ide = db.query(AR2.project_name).filter(
                                AR2.developer_id == developer_id,
                                AR2.application_name == app_name,
                                AR2.project_name.isnot(None),
                                AR2.project_name != 'IDE Work',
                                AR2.project_name != '',
                                AR2.timestamp <= timestamp,
                                AR2.timestamp >= timestamp - timedelta(minutes=30),
                            ).order_by(AR2.timestamp.desc()).first()
                            if recent_ide and recent_ide[0]:
                                project_info['project_name'] = recent_ide[0]
                                project_info['project_type'] = 'Development'
                            else:
                                # Fallback: check FileZilla
                                resolved = resolve_ide_project(db, developer_id, timestamp)
                                if resolved:
                                    project_info['project_name'] = resolved
                                    project_info['project_type'] = 'Development'

                            # Last resort: check concurrent browser/Dia activity for GitHub project context
                            if project_info['project_name'] == 'IDE Work':
                                from models import ActivityRecord as AR_browser
                                recent_browser_proj = db.query(AR_browser.project_name).filter(
                                    AR_browser.developer_id == developer_id,
                                    AR_browser.category == 'browser',
                                    AR_browser.project_name.isnot(None),
                                    AR_browser.project_name != '',
                                    AR_browser.project_name != 'IDE Work',
                                    AR_browser.timestamp <= timestamp,
                                    AR_browser.timestamp >= timestamp - timedelta(minutes=30),
                                ).order_by(AR_browser.timestamp.desc()).first()
                                if recent_browser_proj and recent_browser_proj[0]:
                                    project_info['project_name'] = recent_browser_proj[0]
                                    project_info['project_type'] = 'Development'
                        # Also check if VS Code project name is actually a FileZilla site name
                        elif project_info['project_name'] and category == 'development':
                            resolved = resolve_ide_project(db, developer_id, timestamp, project_info['project_name'])
                            if resolved and resolved != project_info['project_name']:
                                project_info['project_name'] = resolved
                                project_info['project_type'] = 'Development'

                        # For non-development activities (browser, system, etc.),
                        # inherit project from the most recent IDE/editor activity
                        if category != 'development':
                            from models import ActivityRecord as AR
                            recent_dev = db.query(AR.project_name).filter(
                                AR.developer_id == developer_id,
                                AR.category == 'development',
                                AR.project_name.isnot(None),
                                AR.project_name != 'IDE Work',
                                AR.timestamp <= timestamp,
                                AR.timestamp >= timestamp - timedelta(minutes=30),
                            ).order_by(AR.timestamp.desc()).first()
                            if recent_dev and recent_dev[0]:
                                project_info['project_name'] = recent_dev[0]

                        # Look up project_id from projects table, auto-insert if dev editor + valid name + >2h
                        from models import ActivityRecord, Project
                        from project_auto_insert import resolve_or_create_project
                        project_id = resolve_or_create_project(db, project_info['project_name'], app_name, logger)

                        # Create activity record (store developer_id as string, no FK)
                        activity_record = ActivityRecord(
                            developer_id=developer_id,
                            application_name=app_name,
                            window_title=window_title,
                            url=url,
                            file_path=project_info['file_path'],
                            category=category,
                            duration=duration,
                            timestamp=timestamp,
                            project_id=project_id,
                            project_name=project_info['project_name'],
                            project_type=project_info['project_type'],
                            detailed_activity=project_info['detailed_activity']
                        )

                        try:
                            with db.begin_nested():
                                db.add(activity_record)
                            processed_activities += 1
                        except IntegrityError:
                            skipped_duplicates += 1
                            continue
                        
                    except Exception as e:
                        logger.error(f"Error processing event: {e}", exc_info=True)
                        continue
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Synced {processed_activities} new, skipped {skipped_duplicates} duplicates from {developer_id}")

        return {
            "status": "success",
            "message": f"Processed {processed_activities} activities ({skipped_duplicates} duplicates skipped)",
            "developer_id": developer_id,
            "processed": processed_activities,
            "duplicates_skipped": skipped_duplicates,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing ActivityWatch webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/activitywatch/validate-token")
async def validate_token_endpoint(
    developer_id: str,
    token: str
):
    """Test endpoint to validate a token (for debugging)"""
    is_valid = validate_stateless_token(developer_id, token)
    
    return {
        "developer_id": developer_id,
        "token_valid": is_valid,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/activitywatch/developer-summary/{developer_id}")
async def get_developer_summary_stateless(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get activity summary for a developer (no user authentication required)"""
    
    # Parse dates
    if start_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
    if end_date:
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end = datetime.now(timezone.utc)
    
    # Get activities for this developer (by string ID, not FK)
    from models import ActivityRecord
    activities = db.query(ActivityRecord).filter(
        ActivityRecord.developer_id == developer_id,
        ActivityRecord.timestamp >= start,
        ActivityRecord.timestamp <= end
    ).all()
    
    if not activities:
        return {
            "developer_id": developer_id,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "summary": {"total_activities": 0, "total_time": 0, "categories": {}, "projects": {}}
        }
    
    # Process activities into summary
    summary = process_developer_activities(activities)
    
    return {
        "developer_id": developer_id,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": summary
    }

@router.get("/activitywatch/team-summary")
async def get_team_summary_stateless(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get team-wide summary without requiring user authentication"""
    
    # Parse dates
    if start_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
    if end_date:
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end = datetime.now(timezone.utc)
    
    # Get all unique developer IDs from activities
    from sqlalchemy import distinct
    from models import ActivityRecord
    developer_ids = db.query(distinct(ActivityRecord.developer_id)).filter(
        ActivityRecord.developer_id.isnot(None),
        ActivityRecord.timestamp >= start,
        ActivityRecord.timestamp <= end
    ).all()
    
    team_data = []
    total_team_time = 0
    total_team_activities = 0
    
    for (dev_id,) in developer_ids:
        if not dev_id:
            continue
        
        # Get activities for this developer
        activities = db.query(ActivityRecord).filter(
            ActivityRecord.developer_id == dev_id,
            ActivityRecord.timestamp >= start,
            ActivityRecord.timestamp <= end
        ).all()
        
        summary = process_developer_activities(activities)
        total_team_time += summary['total_time']
        total_team_activities += summary['total_activities']
        
        # Extract developer name from ID (reverse engineer from developer_id format)
        developer_name = dev_id.replace('_', ' ').title()
        if '_' in dev_id:
            # Remove hash/year suffix for display
            name_parts = dev_id.split('_')[:-1]  # Remove last part (hash/year)
            developer_name = ' '.join(name_parts).title()
        
        team_data.append({
            "developer_id": dev_id,
            "name": developer_name,
            "summary": summary
        })
    
    return {
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "team_data": team_data,
        "total_developers": len(team_data),
        "team_totals": {
            "total_time": total_team_time,
            "total_time_formatted": f"{total_team_time / 3600:.2f}h",
            "total_activities": total_team_activities
        }
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "mode": "stateless",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "ActivityWatch webhook endpoint is running (stateless mode)"
    }

def process_developer_activities(activities: List) -> Dict:
    """Process activities into summary statistics"""
    if not activities:
        return {
            "total_activities": 0,
            "total_time": 0,
            "categories": {},
            "projects": {},
            "working_hours": 0,
            "productivity_percentage": 0
        }
    
    total_time = sum(activity.duration for activity in activities)
    categories = {}
    projects = {}
    working_hours = 0
    
    for activity in activities:
        category = activity.category or 'other'
        project = activity.project_name or 'Unknown'
        duration = activity.duration
        
        # Category processing
        if category not in categories:
            categories[category] = {"count": 0, "duration": 0}
        categories[category]["count"] += 1
        categories[category]["duration"] += duration
        
        # Project processing
        if project not in projects:
            projects[project] = {"count": 0, "duration": 0, "type": activity.project_type or 'Work'}
        projects[project]["count"] += 1
        projects[project]["duration"] += duration
        
        # Calculate working hours with category weights
        category_weights = {
            'development': 1.0,
            'database': 1.0,
            'productivity': 1.0,
            'browser': 0.85,
            'other': 0.5,
            'system': 0.1,
            'entertainment': 0.0
        }
        
        weight = category_weights.get(category, 0.5)
        working_hours += duration * weight
    
    productivity_percentage = (working_hours / total_time * 100) if total_time > 0 else 0
    
    # Format for frontend
    for category_data in categories.values():
        category_data["duration_formatted"] = f"{category_data['duration'] / 3600:.2f}h"
    
    for project_data in projects.values():
        project_data["duration_formatted"] = f"{project_data['duration'] / 3600:.2f}h"
    
    return {
        "total_activities": len(activities),
        "total_time": total_time,
        "total_time_formatted": f"{total_time / 3600:.2f}h",
        "working_hours": working_hours,
        "working_hours_formatted": f"{working_hours / 3600:.2f}h",
        "productivity_percentage": round(productivity_percentage, 1),
        "categories": categories,
        "projects": projects
    }
