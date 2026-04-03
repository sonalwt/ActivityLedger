# Enhanced activity data API with proper categorization
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, func
from database import get_db
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def format_duration(milliseconds):
    """Convert milliseconds to hours, minutes, seconds"""
    total_seconds = milliseconds / 1000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"

# Application categorization rules
APP_CATEGORIES = {
    'productivity': [
        'code.exe', 'code', 'cursor.exe', 'cursor', 'devenv.exe', 'notepad++.exe',
        'sublime_text.exe', 'atom.exe', 'brackets.exe', 'vim', 'emacs',
        'pycharm.exe', 'pycharm64.exe', 'idea.exe', 'idea64.exe', 'webstorm.exe',
        'phpstorm.exe', 'rubymine.exe', 'goland.exe', 'clion.exe', 'rider.exe',
        'datagrip.exe', 'studio64.exe', 'eclipse.exe', 'netbeans.exe',
        'word.exe', 'winword.exe', 'excel.exe', 'powerpnt.exe', 'outlook.exe',
        'teams.exe', 'slack.exe', 'discord.exe', 'zoom.exe', 'skype.exe',
        'notion.exe', 'obsidian.exe', 'onenote.exe', 'evernote.exe',
        'todoist.exe', 'trello.exe', 'asana.exe', 'clickup.exe',
        'terminal', 'cmd.exe', 'powershell.exe', 'bash', 'git-bash.exe',
        'conemu.exe', 'hyper.exe', 'iterm2', 'warp', 'alacritty',
        'postman.exe', 'insomnia.exe', 'fiddler.exe',
        'tableplus.exe', 'dbeaver.exe', 'heidisql.exe', 'navicat.exe',
        'git.exe', 'gitkraken.exe', 'sourcetree.exe', 'fork.exe',
        'docker.exe', 'dockerdesktop.exe', 'virtualbox.exe', 'vmware.exe',
        'filezilla.exe'
    ],
    'browser': [
        'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe',
        'vivaldi.exe', 'safari', 'iexplore.exe', 'browser'
    ],
    'server': [
        'winscp.exe', 'putty.exe', 'mobaxterm.exe',
        'securecrt.exe', 'xshell.exe', 'royal tsx', 'termius.exe',
        'cyberduck.exe', 'transmit', 'forklift', 'expandrive.exe',
        'mysql.exe', 'psql.exe', 'mongo.exe', 'redis-cli.exe',
        'pgadmin4.exe', 'phpmyadmin', 'adminer', 'sequel pro',
        'mongodb compass.exe', 'robo 3t.exe', 'redis desktop manager.exe',
        'apache', 'nginx', 'httpd', 'node.exe', 'php.exe', 'python.exe'
    ],
    'non-work': [
        'spotify.exe', 'vlc.exe', 'mpv.exe', 'wmplayer.exe', 'itunes.exe',
        'netflix.exe', 'disney+.exe', 'prime video', 'youtube music',
        'steam.exe', 'epicgameslauncher.exe', 'origin.exe', 'uplay.exe',
        'leagueoflegends.exe', 'valorant.exe', 'minecraft.exe', 'roblox.exe',
        'obs.exe', 'obs64.exe', 'streamlabs obs.exe', 'xsplit.exe',
        'photoshop.exe', 'illustrator.exe', 'premiere.exe', 'aftereffects.exe',
        'blender.exe', 'maya.exe', '3dsmax.exe', 'cinema4d.exe',
        'whatsapp.exe', 'telegram.exe', 'signal.exe', 'messenger.exe'
    ]
}

def categorize_activity(app_name: str, window_title: str = "", url: str = "") -> str:
    """Categorize activity based on application name, window title, and URL"""
    if not app_name:
        return 'uncategorized'
    
    app_lower = app_name.lower()
    title_lower = window_title.lower() if window_title else ""
    
    # Check direct app matches
    for category, apps in APP_CATEGORIES.items():
        if any(app in app_lower for app in apps):
            # Special handling for browsers
            if category == 'browser' and url:
                # Check if it's work-related browsing
                work_domains = ['github', 'stackoverflow', 'docs', 'api', 'localhost', 
                               'jira', 'confluence', 'aws', 'azure', 'google cloud']
                if any(domain in url.lower() for domain in work_domains):
                    return 'productivity'
            return category
    
    # Check window title for categorization hints
    if 'youtube' in title_lower or 'netflix' in title_lower:
        return 'non-work'
    
    if any(term in title_lower for term in ['ssh', 'terminal', 'console', 'command']):
        return 'server'
    
    if any(term in title_lower for term in ['.py', '.js', '.html', '.css', '.java', '.cpp']):
        return 'productivity'
    
    return 'uncategorized'

@router.get("/api/activity-data/{developer_id}")
async def get_developer_activity_data(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get categorized activity data for a specific developer"""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Build query
        query = text("""
            SELECT 
                id,
                developer_id,
                application_name,
                window_title,
                url,
                duration,
                timestamp,
                activity_data,
                category,
                project_name
            FROM activity_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            ORDER BY timestamp DESC
        """)
        
        result = db.execute(query, {
            'dev_id': developer_id,
            'start_date': start,
            'end_date': end
        })
        
        activities = []
        total_duration = 0
        category_breakdown = {
            'productivity': 0,
            'browser': 0,
            'server': 0,
            'non-work': 0,
            'uncategorized': 0
        }
        
        for row in result:
            app_name = row[2] or ''
            window_title = row[3] or ''
            url = row[4] or ''
            duration = row[5] or 0
            
            # Parse activity_data JSON if available
            activity_details = {}
            if row[7]:
                try:
                    activity_details = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                except:
                    pass
            
            # Determine category
            if row[8]:  # Use existing category if available
                activity_category = row[8]
            else:
                # Categorize based on our rules
                activity_category = categorize_activity(app_name, window_title, url)
            
            # Filter by category if specified
            if category and activity_category != category:
                continue
            
            activity = {
                'id': row[0],
                'developer_id': row[1],
                'application_name': app_name,
                'window_title': window_title,
                'url': url,
                'duration': duration,
                'timestamp': row[6].isoformat() if row[6] else None,
                'category': activity_category,
                'project_name': row[9],
                'activity_details': activity_details
            }
            
            activities.append(activity)
            total_duration += duration
            category_breakdown[activity_category] += duration
        
        # Convert category durations to percentages
        category_percentages = {}
        for cat, duration in category_breakdown.items():
            category_percentages[cat] = {
                'duration': duration,
                'percentage': round((duration / total_duration * 100) if total_duration > 0 else 0, 1),
                'hours': round(duration / 3600, 2)
            }
        
        return {
            'data': activities,
            "total_time": format_duration(total_duration),
            'total_activities': len(activities),
            'category_breakdown': category_percentages,
            'date_range': {
                'start': start.isoformat(),
                'end': end.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching activity data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/activity-categories/{developer_id}")
async def get_activity_by_categories(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get activity data grouped by categories"""
    try:
        # Get all activities first
        all_data = await get_developer_activity_data(
            developer_id, start_date, end_date, None, db
        )
        
        # Group by category
        categorized_data = {
            'productivity': [],
            'browser': [],
            'server': [],
            'non-work': [],
            'uncategorized': []
        }
        
        for activity in all_data['data']:
            category = activity['category']
            if category in categorized_data:
                categorized_data[category].append(activity)
        
        # Get top apps per category
        category_stats = {}
        for category, activities in categorized_data.items():
            app_durations = {}
            for activity in activities:
                app_name = activity['application_name']
                if app_name not in app_durations:
                    app_durations[app_name] = 0
                app_durations[app_name] += activity['duration']
            
            # Sort apps by duration
            top_apps = sorted(
                app_durations.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            category_stats[category] = {
                'activities': activities[:100],  # Limit to 100 most recent
                'total_activities': len(activities),
                'total_duration': sum(a['duration'] for a in activities)/1000,
                'top_applications': [
                    {
                        'name': app,
                        'duration': duration,
                        'percentage': round((duration / all_data['total_time'] * 100) if all_data['total_time'] > 0 else 0, 1)
                    }
                    for app, duration in top_apps
                ]
            }
        
        return {
            'categories': category_stats,
            'summary': all_data['category_breakdown'],
            'date_range': all_data['date_range']
        }
        
    except Exception as e:
        logger.error(f"Error fetching categorized activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/update-activity-categories")
async def update_activity_categories(db: Session = Depends(get_db)):
    """Update all uncategorized activities with proper categories"""
    try:
        # Get all activities without categories
        query = text("""
            SELECT id, application_name, window_title, url
            FROM activity_records
            WHERE category IS NULL OR category = ''
        """)
        
        result = db.execute(query)
        updated_count = 0
        
        for row in result:
            activity_id = row[0]
            app_name = row[1] or ''
            window_title = row[2] or ''
            url = row[3] or ''
            
            # Determine category
            category = categorize_activity(app_name, window_title, url)
            
            # Update the record
            update_query = text("""
                UPDATE activity_records
                SET category = :category
                WHERE id = :id
            """)
            
            db.execute(update_query, {
                'category': category,
                'id': activity_id
            })
            
            updated_count += 1
        
        db.commit()
        
        return {
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully categorized {updated_count} activities'
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
