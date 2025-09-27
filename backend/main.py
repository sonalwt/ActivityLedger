from fastapi import FastAPI, Depends, HTTPException, status, Request
import json
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from stateless_webhook import router as stateless_router
import uvicorn
import models, schemas, crud, auth, database
from database import SessionLocal, engine
from my_activitywatch_client import ActivityWatchClient
from productivity_calculator import ProductivityCalculator
from realistic_hours_calculator import RealisticHoursCalculator
from developer_discovery import DeveloperDiscovery
from models import DiscoveredDeveloper, ActivityRecord
from concurrent.futures import ThreadPoolExecutor
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import re
from sqlalchemy import text
import requests
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter()


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Timesheet API", version="1.0.0")

# CORS middleware - use environment-aware configuration
from config import Config

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://timesheet.firsteconomy.com",
        "https://timesheet.firsteconomy.com",
        "http://api-timesheet.firsteconomy.com",
        "https://api-timesheet.firsteconomy.com",
        "https://timesheet-api.firsteconomy.com",  # From .env.production
        "*"  # Temporarily allow all origins to debug
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stateless_router, prefix="/api/v1", tags=["stateless-webhook"])

# Add multi-developer support
from simple_multi_dev_api import router as multi_dev_router
app.include_router(multi_dev_router)

# Add the fixed dynamic developer API
from fixed_dynamic_developer_api import router as dynamic_developer_router
app.include_router(dynamic_developer_router, tags=["dynamic-developers"])

# Add real data endpoints

# app.mount("/static", StaticFiles(directory="static"), name="static")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

exec(open('real_data_endpoints.py').read())

class DeveloperRegistration(BaseModel):
    developer_name: str
    api_token: str
    ip_address: Optional[str] = None
    activitywatch_port: Optional[int] = 5600
    hostname: Optional[str] = None
    browser_info: Optional[str] = None
    registration_time: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }




def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth.verify_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except:
        raise credentials_exception
    
    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/api/sync")
async def receive_sync_data(sync_data: dict, db: Session = Depends(get_db)):
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
        
        # Save activity records
        for event in data:
            # Extract event details
            duration = event.get("duration", 0)
            event_data = json.dumps(event.get("data", {}))
            event_timestamp = event.get("timestamp", timestamp)
            
            # Insert into database
            db.execute(text("""
                INSERT INTO activity_records 
                (developer_id, timestamp, duration, activity_data, created_at)
                VALUES (:dev_id, :timestamp, :duration, :data, NOW())
            """), {
                "dev_id": developer_id,
                "timestamp": event_timestamp,
                "duration": duration,
                "data": event_data
            })
        
        db.commit()
        return {"success": True, "received": len(data)}
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/activity-tracker")
async def get_activity_tracker():
    return FileResponse("activity_tracker.html")


@app.get("/activity-data")
def get_activity_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity data from ActivityWatch and store in database"""
    try:
        aw_client = ActivityWatchClient()
        
        # Parse dates or use defaults
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Fetch data from ActivityWatch
        activity_data = aw_client.get_activity_data(start, end)
        
        # Store in database
        for activity in activity_data:
            crud.create_activity_record(db, activity, current_user.id)
        
        # Get processed data for frontend
        processed_data = crud.get_activity_summary(db, current_user.id, start, end)
        
        return {
            "data": processed_data,
            "total_time": sum(item["duration"] for item in processed_data),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching activity data: {str(e)}")

@app.get("/activity-summary")
def get_activity_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity summary from database"""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        summary = crud.get_activity_summary(db, current_user.id, start, end)
        
        return {
            "data": summary,
            "total_time": sum(item["duration"] for item in summary),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting activity summary: {str(e)}")

@app.get("/productivity-analysis")
def get_productivity_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get productivity analysis for the specified date range"""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        calculator = ProductivityCalculator()
        analysis = calculator.calculate_productivity_score_from_activitywatch(start, end)
        
        return {
            "productivity_analysis": analysis,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating productivity: {str(e)}")

@app.get("/daily-hours")
def get_daily_hours(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily working hours report with color coding"""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            # Default to last 7 days
            start = datetime.now(timezone.utc) - timedelta(days=7)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        calculator = RealisticHoursCalculator()
        report = calculator.calculate_daily_report(db, current_user.id, start, end)
        
        return {
            "daily_hours_report": report,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating daily hours: {str(e)}")

@app.get("/top-window-titles")
def get_top_window_titles(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user)
):
    """Get top window titles by duration from ActivityWatch"""
    try:
        aw_client = ActivityWatchClient()
        
        # Parse dates or use defaults
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Get top window titles from ActivityWatch
        top_titles = aw_client.get_top_window_titles(start, end, limit)
        
        # Format duration for frontend
        for title in top_titles:
            title['duration_formatted'] = f"{title['total_duration'] / 3600:.2f}h"
            title['last_seen_formatted'] = title['last_seen'].strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            "top_window_titles": top_titles,
            "total_titles": len(top_titles),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top window titles: {str(e)}")

# Add this to your backend/main.py

@app.get("/activity-tracker")
async def serve_developer_selection_portal():
    """Serve the developer selection portal"""
    return FileResponse("developer_selection_portal.html")

@app.get("/developer-setup")
async def serve_developer_setup():
    return FileResponse("developer-setup.html")    

@app.get("/developers-list")
async def serve_developers_list():
    return FileResponse("developers_list.html")    

@app.get("/api/admin/developers-overview")
async def get_admin_developers_overview(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to get overview of all developers (for the portal)"""
    try:
        from datetime import datetime, timezone
        from sqlalchemy import text
        
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get all developers with activity data
        overview_query = text("""
            SELECT 
                ar.developer_id,
                COUNT(*) as activity_count,
                SUM(ar.duration) as total_duration,
                MAX(ar.timestamp) as last_activity
            FROM activity_records ar
            WHERE ar.developer_id IS NOT NULL
            AND ar.timestamp >= :today
            GROUP BY ar.developer_id
            ORDER BY total_duration DESC
        """)
        
        result = db.execute(overview_query, {"today": today}).fetchall()
        
        developers = []
        total_hours = 0
        active_count = 0
        
        for row in result:
            developer_id = row[0]
            activity_count = row[1]
            duration_seconds = row[2] or 0
            last_activity = row[3]
            
            hours_today = duration_seconds / 3600.0
            total_hours += hours_today
            
            # Check if active (activity in last 30 minutes)
            is_active = False
            if last_activity:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                is_active = time_diff.total_seconds() < 1800  # 30 minutes
                if is_active:
                    active_count += 1
            
            # Calculate productivity estimate
            productivity = min(95, max(0, int(hours_today * 12)))
            
            # Format last seen
            if last_activity:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 3600:
                    last_seen = f"{int(time_diff.total_seconds() / 60)} min ago"
                else:
                    last_seen = f"{int(time_diff.total_seconds() / 3600)}h ago"
            else:
                last_seen = "Never"
            
            developers.append({
                "name": developer_id,
                "is_active": is_active,
                "hours_today": hours_today,
                "productivity": productivity,
                "activities_count": activity_count,
                "last_seen": last_seen
            })
        
        # Calculate overview stats
        avg_productivity = sum(dev["productivity"] for dev in developers) / len(developers) if developers else 0
        
        return {
            "overview": {
                "total_developers": len(developers),
                "active_developers": active_count,
                "total_hours": total_hours,
                "avg_productivity": avg_productivity
            },
            "developers": developers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting developers overview: {str(e)}")

# Alternative endpoint without authentication for the HTML portal
@app.get("/api/public/developers-list")
async def get_public_developers_list(db: Session = Depends(get_db)):
    """Public endpoint to list developers (for portal use)"""
    try:
        from datetime import datetime, timezone
        from sqlalchemy import text
        
        # Get basic developer info
        developers_query = text("""
            SELECT DISTINCT 
                ar.developer_id,
                COUNT(*) as total_activities,
                MAX(ar.timestamp) as last_activity
            FROM activity_records ar
            WHERE ar.developer_id IS NOT NULL
            GROUP BY ar.developer_id
            ORDER BY last_activity DESC NULLS LAST
            LIMIT 50
        """)
        
        result = db.execute(developers_query).fetchall()
        
        developers = []
        for row in result:
            developer_id = row[0]
            total_activities = row[1]
            last_activity = row[2]
            
            # Format last activity
            if last_activity:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 3600:
                    last_seen = f"{int(time_diff.total_seconds() / 60)} min ago"
                elif time_diff.total_seconds() < 86400:
                    last_seen = f"{int(time_diff.total_seconds() / 3600)}h ago"
                else:
                    last_seen = last_activity.strftime('%Y-%m-%d')
                
                is_active = time_diff.total_seconds() < 1800  # 30 minutes
            else:
                last_seen = "Never"
                is_active = False
            
            developers.append({
                "developer_id": developer_id,
                "total_activities": total_activities,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "last_seen": last_seen,
                "is_active": is_active
            })
        
        return {"developers": developers}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing developers: {str(e)}")

@router.get("/api/developers/real-summary")
def get_developers_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    developers = db.query(models.Developer).all()

    total_hours = sum(d.hours_today for d in developers)
    avg_productivity = (sum(d.productivity for d in developers) / len(developers)) if developers else 0
    active_devs = sum(1 for d in developers if d.is_active)

    return {
        "overview": {
            "total_developers": len(developers),
            "active_developers": active_devs,
            "total_hours": total_hours,
            "avg_productivity": avg_productivity,
        },
        "developers": [
            {
                "name": d.name,
                "is_active": d.is_active,
                "hours_today": d.hours_today,
                "productivity": d.productivity,
                "activities_count": d.activities_count,
                "last_seen": d.last_seen.strftime("%Y-%m-%d %H:%M:%S") if d.last_seen else "Never"
            }
            for d in developers
        ]
    }

# @app.post("/api/register-developer")
# async def register_developer(
#     registration: DeveloperRegistration,
#     db: Session = Depends(get_db)
# ):
#     """Simple developer registration with just name and token"""
#     try:
#         # Generate developer ID from name
#         developer_id = generate_developer_id(registration.developer_name)
        
#         # Validate access token format
#         if not registration.api_token.startswith('AWToken_'):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid access token format. Token must start with 'AWToken_'"
#             )
        
#         # Check if developer ID already exists
#         existing_check = db.execute(
#             text("SELECT developer_id FROM developers WHERE developer_id = :dev_id"),
#             {"dev_id": developer_id}
#         ).fetchone()
        
#         if existing_check:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Developer ID '{developer_id}' already exists. Please use a different name."
#             )
        
#         # Check if token is already used
#         token_check = db.execute(
#             text("SELECT developer_id FROM developers WHERE api_token = :token"),
#             {"token": registration.api_token}
#         ).fetchone()
        
#         if token_check:
#             raise HTTPException(
#                 status_code=400,
#                 detail="This access token is already in use by another developer."
#             )
        
#         # Test ActivityWatch connectivity (optional - don't fail if not available)
#         activitywatch_status = "unknown"
#         if registration.ip_address:
#             try:
#                 aw_url = f"http://{registration.ip_address}:{registration.activitywatch_port}"
#                 response = requests.get(f"{aw_url}/api/0/info", timeout=3)
#                 if response.status_code == 200:
#                     activitywatch_status = "connected"
#                 else:
#                     activitywatch_status = "not_responding"
#             except:
#                 activitywatch_status = "unreachable"
        
#         # Insert new developer
#         insert_query = text("""
#             INSERT INTO developers (
#                 developer_id,
#                 name,
#                 api_token,
#                 ip_address,
#                 activitywatch_port,
#                 hostname,
#                 active,
#                 created_at,
#                 browser_info,
#                 activitywatch_status
#             ) VALUES (
#                 :developer_id,
#                 :name,
#                 :api_token,
#                 :ip_address,
#                 :activitywatch_port,
#                 :hostname,
#                 :active,
#                 :created_at,
#                 :browser_info,
#                 :activitywatch_status
#             )
#         """)
        
#         db.execute(insert_query, {
#             "developer_id": developer_id,
#             "name": registration.developer_name,
#             "api_token": registration.api_token,
#             "ip_address": registration.ip_address or "127.0.0.1",
#             "activitywatch_port": registration.activitywatch_port or 5600,
#             "hostname": registration.hostname or "unknown",
#             "active": True,
#             "created_at": datetime.now(timezone.utc),
#             "browser_info": registration.browser_info,
#             "activitywatch_status": activitywatch_status
#         })
        
#         db.commit()
        
#         # Log successful registration
#         print(f"✅ Developer registered: {developer_id} ({registration.developer_name})")
        
#         return {
#             "success": True,
#             "message": "Developer registered successfully",
#             "developer_id": developer_id,
#             "developer_name": registration.developer_name,
#             "activitywatch_status": activitywatch_status,
#             "monitoring_starts": "Data collection will begin immediately",
#             "portal_access": f"Developer will appear in portal as '{registration.developer_name}'"
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         print(f"❌ Registration failed for {registration.developer_name}: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Registration failed: {str(e)}"
#         )

def generate_developer_id(name: str) -> str:
    """Generate a clean developer ID from name"""
    # Remove special characters and convert to lowercase
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    # Replace spaces with underscores
    developer_id = re.sub(r'\s+', '_', clean_name.strip().lower())
    # Limit length
    developer_id = developer_id[:50]
    
    if not developer_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid name: could not generate developer ID"
        )
    
    return developer_id

@app.get("/api/test-developer-connection")
async def test_developer_connection(
    developer_id: str,
    ip_address: str,
    activitywatch_port: int = 5600
):
    """Test connection to developer's ActivityWatch instance"""
    try:
        aw_url = f"http://{ip_address}:{activitywatch_port}"
        
        # Test info endpoint
        info_response = requests.get(f"{aw_url}/api/0/info", timeout=5)
        if info_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"ActivityWatch not responding at {aw_url}"
            )
        
        info_data = info_response.json()
        
        # Test buckets endpoint
        buckets_response = requests.get(f"{aw_url}/api/0/buckets", timeout=5)
        if buckets_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Could not access ActivityWatch buckets"
            )
        
        buckets_data = buckets_response.json()
        
        return {
            "success": True,
            "message": "ActivityWatch connection successful",
            "activitywatch_version": info_data.get("version", "unknown"),
            "available_buckets": len(buckets_data),
            "bucket_names": list(buckets_data.keys())[:5],  # First 5 bucket names
            "connection_url": aw_url
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )

# Serve the registration form
@app.get("/register-developer")
async def serve_registration_form():
    """Serve the developer registration form"""
    return FileResponse("simple_developer_registration.html")


# IMMEDIATE FIX - Replace your registration endpoint in main.py with this:

# FIXED Registration Endpoint - Replace in your main.py

# FINAL CORRECT Registration Endpoint - Replace in your main.py

@app.post("/api/register-developer")
async def register_developer(
    registration: DeveloperRegistration,
    db: Session = Depends(get_db)
):
    """Developer registration with proper table structure"""
    try:
        # Generate developer ID from name
        developer_id = generate_developer_id(registration.developer_name)
        
        # Validate access token format
        if not registration.api_token.startswith('AWToken_'):
            raise HTTPException(
                status_code=400,
                detail="Invalid access token format. Token must start with 'AWToken_'"
            )
        
        # Check if developer_id already exists
        existing_dev = db.execute(
            text("SELECT id FROM developers WHERE developer_id = :dev_id"),
            {"dev_id": developer_id}
        ).fetchone()
        
        if existing_dev:
            raise HTTPException(
                status_code=400,
                detail=f"Developer ID '{developer_id}' already exists. Please use a different name."
            )
        
        # Check if name already exists
        existing_name = db.execute(
            text("SELECT id FROM developers WHERE name = :name"),
            {"name": registration.developer_name}
        ).fetchone()
        
        if existing_name:
            raise HTTPException(
                status_code=400,
                detail=f"Developer name '{registration.developer_name}' already exists. Please use a different name."
            )
        
        # Check if api_token already exists
        existing_token = db.execute(
            text("SELECT id FROM developers WHERE api_token = :token"),
            {"token": registration.api_token}
        ).fetchone()
        
        if existing_token:
            raise HTTPException(
                status_code=400,
                detail="This access token is already in use by another developer."
            )
        
        # Insert new developer using the correct table structure
        insert_query = text("""
            INSERT INTO developers (
                developer_id,
                name,
                email,
                active,
                api_token,
                created_at
            ) VALUES (
                :developer_id,
                :name,
                :email,
                :active,
                :api_token,
                :created_at
            )
        """)
        
        db.execute(insert_query, {
            "developer_id": developer_id,
            "name": registration.developer_name,
            "email": f"{developer_id}@company.com",
            "active": True,
            "api_token": registration.api_token,
            "created_at": datetime.now(timezone.utc)
        })
        
        db.commit()
        
        print(f"✅ Developer registered: {developer_id} ({registration.developer_name})")
        
        return {
            "success": True,
            "message": "Developer registered successfully",
            "developer_id": developer_id,
            "developer_name": registration.developer_name,
            "monitoring_starts": "Data collection will begin immediately",
            "portal_access": f"Developer will appear in portal as '{registration.developer_name}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Registration failed for {registration.developer_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

# Also add this endpoint to serve the registration form
@app.get("/register-developer")
async def serve_registration_form():
    """Serve the developer registration form"""
    return FileResponse("register-developer.html")

# API to check registration status
@app.get("/api/developer-status/{developer_id}")
async def get_developer_status(
    developer_id: str,
    db: Session = Depends(get_db)
):
    """Get current status of a registered developer"""
    try:
        status_query = text("""
            SELECT 
                d.developer_id,
                d.name,
                d.active,
                d.created_at,
                d.last_sync,
                d.ip_address,
                d.activitywatch_port,
                d.activitywatch_status,
                COUNT(ar.id) as recent_activities
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id 
                AND ar.created_at > NOW() - INTERVAL '1 hour'
            WHERE d.developer_id = :dev_id
            GROUP BY d.developer_id, d.name, d.active, d.created_at, d.last_sync, 
                     d.ip_address, d.activitywatch_port, d.activitywatch_status
        """)
        
        result = db.execute(status_query, {"dev_id": developer_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        return {
            "developer_id": result[0],
            "name": result[1],
            "active": result[2],
            "registered_at": result[3].isoformat() if result[3] else None,
            "last_sync": result[4].isoformat() if result[4] else None,
            "ip_address": result[5],
            "activitywatch_port": result[6],
            "activitywatch_status": result[7],
            "recent_activities": result[8],
            "status": "monitoring" if result[8] > 0 else "registered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting developer status: {str(e)}"
        )

# Add this function to your existing main.py
@app.get("/setup-database")
async def setup_database_schema(db: Session = Depends(get_db)):
    """One-time setup for new database columns"""
    try:
        updates = [
            "ALTER TABLE developers ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45) DEFAULT '127.0.0.1'",
            "ALTER TABLE developers ADD COLUMN IF NOT EXISTS activitywatch_port INTEGER DEFAULT 5600",
            "ALTER TABLE developers ADD COLUMN IF NOT EXISTS hostname VARCHAR(255) DEFAULT 'unknown'",
            "ALTER TABLE developers ADD COLUMN IF NOT EXISTS browser_info VARCHAR(255)",
            "ALTER TABLE developers ADD COLUMN IF NOT EXISTS activitywatch_status VARCHAR(50) DEFAULT 'unknown'"
        ]
        
        for update in updates:
            db.execute(text(update))
        
        db.commit()
        
        return {"success": True, "message": "Database schema updated successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
