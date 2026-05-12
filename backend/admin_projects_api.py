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

class MergePayload(BaseModel):
    source_id: Optional[int] = None   # project to deactivate after merge (None in add-mode)
    extra_keywords: List[str] = []     # keywords from the form being merged in


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


def _auto_keywords_from_name(name: str) -> list:
    """Split project name into words to use as auto-generated keywords.
    Splits on spaces, hyphens, and underscores; filters words shorter than 3 chars.
    Example: "Mahindra Manulife" → ["mahindra", "manulife"]
    """
    import re
    words = re.split(r'[\s\-_]+', name.strip().lower())
    return [w for w in words if len(w) >= 3]


def _build_name_like_conditions(project_name: str, param_prefix: str = "nm") -> tuple:
    """
    Build SQL ILIKE conditions and params for matching activity records against an
    admin project name — no manual keywords required.

    Strategy (all applied with OR logic):
      1. Full normalised name as substring:
            project_name ILIKE '%activityledger%'
      2. Each significant word (≥3 chars) as substring:
            project_name ILIKE '%activity%' OR project_name ILIKE '%ledger%'

    Hyphens and underscores in stored values are collapsed to spaces before comparison
    so "activity-ledger" correctly matches the token "activity".

    Returns (conditions: list[str], params: dict).
    """
    import re

    conditions: list = []
    params: dict = {}

    # Normalise: collapse separators → single space, lowercase
    norm = re.sub(r'[\s\-_]+', ' ', project_name.strip().lower())

    # Strategy 1: full name substring
    pk = f"{param_prefix}_full"
    params[pk] = f"%{norm}%"
    conditions.append(
        f"REPLACE(LOWER(COALESCE(ar.project_name, '')), '-', ' ') ILIKE :{pk}"
    )
    conditions.append(
        f"REPLACE(LOWER(COALESCE(ar.window_title, '')), '-', ' ') ILIKE :{pk}"
    )

    # Strategy 2: individual word tokens
    words = [w for w in norm.split() if len(w) >= 3]
    for i, word in enumerate(words):
        pk = f"{param_prefix}_w{i}"
        params[pk] = f"%{word}%"
        conditions.append(
            f"REPLACE(LOWER(COALESCE(ar.project_name, '')), '-', ' ') ILIKE :{pk}"
        )
        conditions.append(
            f"REPLACE(LOWER(COALESCE(ar.window_title, '')), '-', ' ') ILIKE :{pk}"
        )
        conditions.append(
            f"LOWER(COALESCE(ar.url, '')) ILIKE :{pk}"
        )

    return conditions, params


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

    # Normalize keywords; auto-generate from project name if none provided
    cleaned = [k.strip().lower() for k in payload.keywords if k.strip()]
    if not cleaned:
        cleaned = _auto_keywords_from_name(payload.name)

    result = db.execute(text("""
        INSERT INTO projects (name, description, keywords, is_active, total_cost, created_at)
        VALUES (:name, :description, CAST(:keywords AS jsonb), true, :total_cost, NOW())
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
# GET /api/admin/projects/similar  — name-prefix detection
# ============================================================

@router.get("/api/admin/projects/similar")
async def admin_similar_projects(
    name: str = Query(..., min_length=3),
    exclude_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Return active projects whose name starts with, or is a prefix of, the given name."""
    name_lower = name.strip().lower()
    params: dict = {"name": name_lower}
    exclude_clause = ""
    if exclude_id is not None:
        exclude_clause = "AND id != :exclude_id"
        params["exclude_id"] = exclude_id

    rows = db.execute(text(f"""
        SELECT id, name, keywords
        FROM projects
        WHERE is_active = true
          AND LOWER(name) != :name
          AND (
              LOWER(name) LIKE :name || '%'
              OR :name LIKE LOWER(name) || '%'
          )
          {exclude_clause}
        LIMIT 5
    """), params).fetchall()

    return {
        "projects": [
            {"id": r[0], "name": r[1], "keywords": _parse_keywords(r[2])}
            for r in rows
        ]
    }


# ============================================================
# GET /api/admin/projects/activity-names  — project names seen in activity records
# ============================================================

@router.get("/api/admin/projects/activity-names")
async def admin_activity_project_names(
    query: str = Query(""),
    db: Session = Depends(get_db)
):
    """
    Return distinct project_name values from activity_records that are similar
    to the query string. Used to suggest keywords when adding/editing a project.
    """
    q = query.strip().lower()
    if q:
        rows = db.execute(text("""
            SELECT project_name, COUNT(*) AS cnt
            FROM activity_records
            WHERE project_name IS NOT NULL
              AND project_name != ''
              AND (
                  LOWER(REPLACE(project_name, '-', ' ')) LIKE :q || '%'
                  OR LOWER(REPLACE(project_name, '-', ' ')) LIKE '%' || :q || '%'
                  OR :q LIKE LOWER(REPLACE(project_name, '-', ' ')) || '%'
              )
            GROUP BY project_name
            ORDER BY cnt DESC
            LIMIT 10
        """), {"q": q}).fetchall()
    else:
        # No query — return top names from last 30 days
        rows = db.execute(text("""
            SELECT project_name, COUNT(*) AS cnt
            FROM activity_records
            WHERE project_name IS NOT NULL
              AND project_name != ''
              AND timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY project_name
            ORDER BY cnt DESC
            LIMIT 20
        """)).fetchall()

    return {"names": [{"name": r[0], "count": r[1]} for r in rows]}


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
        SET keywords = CAST(:keywords AS jsonb)
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
    try:
        # Duplicate name check (exclude current project)
        existing = db.execute(
            text("SELECT id FROM projects WHERE LOWER(name) = LOWER(:name) AND id != :id"),
            {"name": payload.name.strip(), "id": project_id}
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Another project with this name already exists")

        cleaned = [k.strip().lower() for k in payload.keywords if k.strip()]
        if not cleaned:
            cleaned = _auto_keywords_from_name(payload.name)

        result = db.execute(text("""
            UPDATE projects
            SET name = :name,
                description = :description,
                keywords = CAST(:keywords AS jsonb),
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"admin_update_project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
# POST /api/admin/projects/{id}/merge
# ============================================================

@router.post("/api/admin/projects/{project_id}/merge")
async def admin_merge_into_project(
    project_id: int,
    payload: MergePayload,
    db: Session = Depends(get_db)
):
    """
    Merge keywords into target project.
    - Adds extra_keywords + source project's keywords to the target.
    - If source_id provided, deactivates the source project.
    """
    target = db.execute(
        text("SELECT id, name, keywords FROM projects WHERE id = :id AND is_active = true"),
        {"id": project_id}
    ).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Target project not found or inactive")

    target_keywords = _parse_keywords(target[2])

    source_keywords: list = []
    if payload.source_id:
        source = db.execute(
            text("SELECT keywords FROM projects WHERE id = :id"),
            {"id": payload.source_id}
        ).fetchone()
        if source:
            source_keywords = _parse_keywords(source[0])

    extra = [k.strip().lower() for k in payload.extra_keywords if k.strip()]
    # Merge: preserve order, deduplicate
    seen: set = set(target_keywords)
    merged = list(target_keywords)
    for kw in source_keywords + extra:
        if kw not in seen:
            seen.add(kw)
            merged.append(kw)

    db.execute(text("""
        UPDATE projects SET keywords = CAST(:keywords AS jsonb) WHERE id = :id
    """), {"keywords": json.dumps(merged), "id": project_id})

    if payload.source_id:
        db.execute(
            text("UPDATE projects SET is_active = false WHERE id = :id"),
            {"id": payload.source_id}
        )

    db.commit()
    return {"id": project_id, "name": target[1], "keywords": merged, "message": "Merged successfully"}


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
    Return developer breakdown for a project using intelligent auto-matching.

    Matching strategy (no manual keywords required):
    - Full normalised project name: ILIKE '%mahindra manulife%'
    - Each word token (≥3 chars):   ILIKE '%mahindra%', ILIKE '%manulife%'
    - Applied across project_name, window_title, and url fields (OR logic).
    - Existing keywords (if any) are also honoured for backward compatibility.
    - Hyphens/underscores in stored values are normalised to spaces before comparison.
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

    # ------------------------------------------------------------------ #
    # Smart auto-matching using SQL ILIKE %...% operators.               #
    # The admin never needs to type keywords — the system matches        #
    # activity records by the project name and its individual word       #
    # tokens directly in SQL.                                            #
    # ------------------------------------------------------------------ #

    conditions: list = []
    params: dict = {}

    # 1. Keyword conditions — backward-compat for existing projects that
    #    already have keywords stored (also covers URL / window_title).
    for i, kw in enumerate(keywords):
        conditions.append(
            f"REPLACE(LOWER(COALESCE(ar.project_name, '')), '-', ' ') ILIKE :kw_{i}"
        )
        conditions.append(
            f"REPLACE(LOWER(COALESCE(ar.window_title, '')), '-', ' ') ILIKE :kw_{i}"
        )
        conditions.append(
            f"LOWER(COALESCE(ar.url, '')) ILIKE :kw_{i}"
        )
        params[f"kw_{i}"] = f"%{kw}%"

    # 2. Intelligent name-based LIKE matching — runs purely in SQL.
    #    Covers full project name AND every significant word token.
    name_conds, name_params = _build_name_like_conditions(proj[1], param_prefix="nm")
    conditions.extend(name_conds)
    params.update(name_params)

    if conditions:
        where_clause = f"({' OR '.join(conditions)})"
    else:
        # Should not normally be reached, but safe fallback
        where_clause = "LOWER(COALESCE(ar.project_name, '')) = LOWER(:exact_name)"
        params["exact_name"] = proj[1]

    params["start_date"] = start_utc
    params["end_date"] = end_utc

    rows = db.execute(text(f"""
        SELECT
            ar.developer_id,
            d.name                                    AS developer_name,
            ROUND(SUM(ar.duration) / 3600.0, 2)      AS total_hours,
            ARRAY_AGG(DISTINCT ar.project_name)
                FILTER (WHERE ar.project_name IS NOT NULL AND ar.project_name != '')
                                                      AS matched_project_names,
            ARRAY_AGG(DISTINCT ar.application_name)
                FILTER (WHERE (ar.project_name IS NULL OR ar.project_name = '')
                          AND ar.application_name IS NOT NULL)
                                                      AS matched_browser_apps
        FROM activity_records ar
        LEFT JOIN developers d ON ar.developer_id = d.developer_id
        WHERE {where_clause}
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
        matched_ide = [n for n in (row[3] or []) if n]
        matched_browser = [n for n in (row[4] or []) if n]
        developers.append({
            "developer_id": row[0],
            "developer_name": row[1] or row[0],
            "total_hours": dev_hours,
            "matched_project_names": matched_ide,
            "matched_browser_apps": matched_browser,
        })

    return {
        "project_id": project_id,
        "project_name": proj[1],
        "period": f"{year}-{str(mon).zfill(2)}",
        "developers": developers,
        "total_hours": round(total_hours, 2),
    }
