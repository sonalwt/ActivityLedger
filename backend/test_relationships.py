from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/api/test/relationships")
def test_relationships(db: Session = Depends(get_db)):
    """Test endpoint for relationships - to be implemented"""
    return {"message": "Test relationships endpoint - not implemented yet"}
