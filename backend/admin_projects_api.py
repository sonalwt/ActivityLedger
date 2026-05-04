"""
Admin Projects API — keyword-based project management.

Endpoints:
  GET    /api/admin/projects                    — list all projects with keywords
  POST   /api/admin/projects                    — create project with name + keywords
  PUT    /api/admin/projects/{id}/keywords      — replace keywords for a project
  DELETE /api/admin/projects/{id}               — deactivate a project
  GET    /api/admin/projects/{id}/developers    — developer breakdown matched by keywords
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from database import get_db
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: List[str] = []
    total_cost: Optional[float] = 0

class KeywordsUpdate(BaseModel):
    keywords: List[str]

class ProjectUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: List[str] = []
    total_cost: Optional[float] = 0


# ============================================================
# HELPERS
# ============================================================

def _parse_keywords(raw) -> list:
    """Safely parse keywords from DB value (may be list, str, or None)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return []


def _ist_month_range(year: int, month: int):
    """Return UTC start/end datetimes for a calendar month in IST (UTC+5:30)."""
    ist_offset = timedelta(hours=5, minutes=30)
    # IST month start = midnight IST on day 1 = UTC day 1 00:00 - 5:30
    start_utc = datetime(year, month, 1, tzinfo=timezone.utc) - ist_offset
    if month == 12:
        end_utc = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - ist_offset
    else:
        end_utc = datetime(year, month + 1, 1, tzinfo=timezone.utc) - ist_offset
    return start_utc, end_utc


# ============================================================
# GET /api/admin/projects
# ============================================================

@router.get("/api/admin/projects")
async def admin_list_projects(db: Session = Depends(get_db)):
    """List all projects (active + inactive) with their keywords."""
    rows = db.execute(text("""
        SELECT id, name, description, keywords, is_active, total_cost, created_at
        FROM projects
        ORDER BY is_active DESC, created_at DESC
    """)).fetchall()

    projects = []
    for row in rows:
        projects.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "keywords": _parse_keywords(row[3]),
            "is_active": row[4],
            "total_cost": row[5] or 0,
            "created_at": row[6].isoformat() if row[6] else None,
        })
    return {"projects": projects, "total": len(projects)}


# ============================================================
# POST /api/admin/projects
# ============================================================

@router.post("/api/admin/projects", status_code=201)
async def admin_create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project with optional keywords."""
    # Duplicate check (case-insensitive)
    existing = db.execute(
        text("SELECT id FROM projects WHERE LOWER(name) = LOWER(:name)"),
        {"name": payload.name.strip()}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="A project with this name already exists")

    # Normalize keywords
    cleaned = [k.strip().lower() for k in payload.keywords if k.strip()]

    result = db.execute(text("""
        INSERT INTO projects (name, description, keywords, is_active, total_cost, created_at)
        VALUES (:name, :description, :keywords::jsonb, true, :total_cost, NOW())
        RETURNING id
    """), {
        "name": payload.name.strip(),
        "description": payload.description,
        "keywords": json.dumps(cleaned),
        "total_cost": payload.total_cost or 0,
    })
    new_id = result.fetchone()[0]
    db.commit()

    return {"id": new_id, "name": payload.name.strip(), "keywords": cleaned, "message": "Project created"}


# ============================================================
# PUT /api/admin/projects/{id}/keywords
# ============================================================

@router.put("/api/admin/projects/{project_id}/keywords")
async def admin_update_keywords(
    project_id: int,
    payload: KeywordsUpdate,
    db: Session = Depends(get_db)
):
    """Replace the keyword list for a project."""
    # Normalize: lowercase + strip
    cleaned = [k.strip().lower() for k in payload.keywords if k.strip()]

    result = db.execute(text("""
        UPDATE projects
        SET keywords = :keywords::jsonb
        WHERE id = :id
        RETURNING id
    """), {"keywords": json.dumps(cleaned), "id": project_id})

    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()

    return {"id": project_id, "keywords": cleaned}


# ============================================================
# PUT /api/admin/projects/{id}  — full update
# ============================================================

@router.put("/api/admin/projects/{project_id}")
async def admin_update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update name, description, cost and keywords for a project."""
    # Duplicate name check (exclude current project)
    existing = db.execute(
        text("SELECT id FROM projects WHERE LOWER(name) = LOWER(:name) AND id != :id"),
        {"name": payload.name.strip(), "id": project_id}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Another project with this name already exists")

    cleaned = [k.strip().lower() for k in payload.keywords if k.strip()]

    result = db.execute(text("""
        UPDATE projects
        SET name = :name,
            description = :description,
            keywords = :keywords::jsonb,
            total_cost = :total_cost
        WHERE id = :id
        RETURNING id
    """), {
        "name": payload.name.strip(),
        "description": payload.description,
        "keywords": json.dumps(cleaned),
        "total_cost": payload.total_cost or 0,
        "id": project_id,
    })
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()

    return {"id": project_id, "name": payload.name.strip(), "keywords": cleaned, "message": "Project updated"}


# ============================================================
# DELETE /api/admin/projects/{id}
# ============================================================

@router.delete("/api/admin/projects/{project_id}")
async def admin_delete_project(project_id: int, db: Session = Depends(get_db)):
    """Soft-delete a project (sets is_active = false)."""
    result = db.execute(
        text("UPDATE projects SET is_active = false WHERE id = :id RETURNING id"),
        {"id": project_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()

    return {"message": f"Project {project_id} deactivated"}


# ============================================================
# PUT /api/admin/projects/{id}/reactivate
# ============================================================

@router.put("/api/admin/projects/{project_id}/reactivate")
async def admin_reactivate_project(project_id: int, db: Session = Depends(get_db)):
    """Reactivate a soft-deleted project (sets is_active = true)."""
    result = db.execute(
        text("UPDATE projects SET is_active = true WHERE id = :id RETURNING id"),
        {"id": project_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()

    return {"message": f"Project {project_id} reactivated"}


# ============================================================
# GET /api/admin/projects/{id}/developers
# ============================================================

@router.get("/api/admin/projects/{project_id}/developers")
async def admin_project_developers(
    project_id: int,
    month: Optional[str] = Query(None, description="YYYY-MM format, defaults to current month"),
    db: Session = Depends(get_db)
):
    """
    Return developer breakdown for a project matched by keywords.

    Keyword matching:
    - Hyphens in project_name are replaced with spaces before ILIKE comparison,
      so keyword "mahindra" matches both "mahindra-manulife-distributor" and "mahindra manulife".
    - Multiple keywords use OR logic: any keyword match counts.
    - If project has no keywords, falls back to exact name match (legacy mode).
    """
    # Fetch project
    proj = db.execute(
        text("SELECT id, name, keywords FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    keywords = _parse_keywords(proj[2])

    # Resolve month
    if month:
        try:
            year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    else:
        now = datetime.now(timezone.utc)
        year, mon = now.year, now.month

    start_utc, end_utc = _ist_month_range(year, mon)

    # Build WHERE clause for keyword matching
    if keywords:
        # Normalize hyphens in project_name → space, then ILIKE '%keyword%'
        conditions = " OR ".join(
            f"REPLACE(LOWER(ar.project_name), '-', ' ') ILIKE :kw_{i}"
            for i in range(len(keywords))
        )
        where_clause = f"({conditions})"
        params: dict = {f"kw_{i}": f"%{kw}%" for i, kw in enumerate(keywords)}
    else:
        # Legacy: exact name match (case-insensitive)
        where_clause = "LOWER(ar.project_name) = LOWER(:exact_name)"
        params = {"exact_name": proj[1]}

    params["start_date"] = start_utc
    params["end_date"] = end_utc

    rows = db.execute(text(f"""
        SELECT
            ar.developer_id,
            d.name                               AS developer_name,
            ROUND(SUM(ar.duration) / 3600.0, 2) AS total_hours,
            ARRAY_AGG(DISTINCT ar.project_name)  AS matched_names
        FROM activity_records ar
        LEFT JOIN developers d ON ar.developer_id = d.developer_id
        WHERE {where_clause}
          AND ar.project_name IS NOT NULL
          AND ar.project_name != ''
          AND ar.timestamp >= :start_date
          AND ar.timestamp <  :end_date
        GROUP BY ar.developer_id, d.name
        ORDER BY total_hours DESC
    """), params).fetchall()

    developers = []
    total_hours = 0.0
    for row in rows:
        dev_hours = float(row[2]) if row[2] else 0.0
        total_hours += dev_hours
        matched = [n for n in (row[3] or []) if n]
        developers.append({
            "developer_id": row[0],
            "developer_name": row[1] or row[0],
            "total_hours": dev_hours,
            "matched_project_names": matched,
        })

    return {
        "project_id": project_id,
        "project_name": proj[1],
        "keywords": keywords,
        "period": f"{year}-{str(mon).zfill(2)}",
        "developers": developers,
        "total_hours": round(total_hours, 2),
    }
