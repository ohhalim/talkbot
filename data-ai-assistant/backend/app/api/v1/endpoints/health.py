from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """기본 헬스 체크"""
    return {"status": "healthy", "service": "Data AI Assistant"}


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """상세 헬스 체크 (DB 연결 등 확인)"""
    try:
        # 데이터베이스 연결 확인
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "components": {
            "database": db_status,
            "environment": settings.ENVIRONMENT
        }
    }