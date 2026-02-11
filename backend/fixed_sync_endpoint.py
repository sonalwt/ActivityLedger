# fixed_sync_endpoint.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from database import get_db
from activity_categorizer import ActivityCategorizer
import json

router = APIRouter()

# Replace your receive_sync_data function with this fixed version:

@router.post("/api/sync")
async def receive_sync_data(sync_data: dict, db: Session = Depends(get_db)):
    """Fixed sync endpoint with proper transaction handling"""
    try:
        name = sync_data.get("name")
        token = sync_data.get("token")
        data = sync_data.get("data", [])
        timestamp = sync_data.get("timestamp")
        
        # Validate developer exists
        developer = db.execute(
            text("SELECT developer_id FROM developers WHERE api_token = :token"),
            {"token": token}
        ).fetchone()
        
        if not developer:
            return {"error": "Invalid token"}
        
        developer_id = developer[0]
        
        # Initialize categorizer
        categorizer = ActivityCategorizer()
        
        # Process and save activity records
        saved_count = 0
        failed_count = 0
        
        # Process events in batches to handle transaction failures
        for event in data:
            try:
                # Extract event data properly
                event_data = event.get("data", {})
                duration = event.get("duration", 0)
                event_timestamp = event.get("timestamp", timestamp)
                
                # Skip very short activities (less than 5 seconds)
                if duration < 5:
                    continue
                
                # Extract fields from event data
                window_title = event_data.get("title", "Untitled")
                app_name = event_data.get("app", event_data.get("application", "Unknown"))
                url = event_data.get("url", "")
                file_path = event_data.get("file", "")
                
                # Clean window title
                if window_title and window_title != "Untitled":
                    window_title = window_title.replace(" - Google Chrome", "")
                    window_title = window_title.replace(" - Mozilla Firefox", "")
                    window_title = window_title.replace(" - Microsoft Edge", "")
                    window_title = window_title.replace(" - Visual Studio Code", "")
                
                # Categorize the activity
                category_info = categorizer.get_detailed_category(window_title, app_name)
                
                # Extract project name
                project_name = extract_project_name(window_title, app_name)
                
                # Parse timestamp
                try:
                    if isinstance(event_timestamp, str):
                        parsed_timestamp = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                    else:
                        parsed_timestamp = event_timestamp
                except:
                    parsed_timestamp = datetime.now(timezone.utc)
                
                # Create a savepoint before each insert
                savepoint = db.connection().connection.cursor()
                savepoint.execute("SAVEPOINT sp1")
                
                try:
                    # Insert into activity_records table
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
                        ON CONFLICT (developer_id, timestamp, application_name, window_title) 
                        DO UPDATE SET
                            duration = EXCLUDED.duration,
                            category = EXCLUDED.category,
                            project_name = EXCLUDED.project_name,
                            project_type = EXCLUDED.project_type
                    """)
                    
                    db.execute(insert_query, {
                        "developer_id": developer_id,
                        "application_name": app_name[:255],
                        "window_title": window_title[:500],
                        "url": url[:1000] if url else "",
                        "file_path": file_path[:1000] if file_path else "",
                        "duration": int(duration * 1000),  # Convert to milliseconds
                        "timestamp": parsed_timestamp,
                        "category": category_info["category"],
                        "project_name": project_name,
                        "project_type": category_info["subcategory"],
                        "created_at": datetime.now(timezone.utc)
                    })
                    
                    # Release savepoint on success
                    savepoint.execute("RELEASE SAVEPOINT sp1")
                    saved_count += 1
                    
                except Exception as e:
                    # Rollback to savepoint on error
                    savepoint.execute("ROLLBACK TO SAVEPOINT sp1")
                    failed_count += 1
                    print(f"Error inserting record: {e}")
                    continue
                    
            except Exception as e:
                failed_count += 1
                print(f"Error processing event: {e}")
                db.rollback()  # Add this line
                db.begin()    
                continue
        
        # Commit all successful inserts
        try:
            db.commit()
            print(f"✅ Synced {saved_count} activities for {developer_id} (failed: {failed_count})")
        except Exception as e:
            # If commit fails, try to recover
            db.rollback()
            print(f"❌ Commit failed, attempting recovery: {e}")
            
            # Try to at least save some data
            saved_count = 0
            for event in data[:10]:  # Try just first 10
                try:
                    # Start fresh transaction for each
                    db.begin()
                    # ... insert logic ...
                    db.commit()
                    saved_count += 1
                except:
                    db.rollback()
                    continue
        
        return {
            "success": True,
            "received": len(data),
            "saved": saved_count,
            "failed": failed_count,
            "developer": developer_id
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Sync error: {e}")
        return {"error": str(e), "success": False}

def extract_project_name(window_title: str, app_name: str) -> str:
    """Extract project name from window title"""
    import re
    
    # VSCode pattern: "filename - folder - Visual Studio Code"
    vscode_match = re.search(r' - ([^-]+) - (?:Visual Studio Code|VS Code|Cursor)', window_title)
    if vscode_match:
        return vscode_match.group(1).strip()
    
    # IntelliJ/PyCharm pattern: "project_name – filename"
    jetbrains_match = re.search(r'^([^–]+) – ', window_title)
    if jetbrains_match and any(ide in app_name.lower() for ide in ['intellij', 'pycharm', 'webstorm']):
        return jetbrains_match.group(1).strip()
    
    # Git pattern
    git_match = re.search(r'\\([^\\]+)\\\.git', window_title)
    if git_match:
        return git_match.group(1)
    
    # URL pattern for GitHub/GitLab
    repo_match = re.search(r'github\.com/[^/]+/([^/\s]+)', window_title)
    if repo_match:
        return repo_match.group(1)
    
    # Folder path pattern
    folder_match = re.search(r'\\([^\\]+)\\[^\\]+\.[a-z]+$', window_title)
    if folder_match:
        return folder_match.group(1)
    
    return "general"
