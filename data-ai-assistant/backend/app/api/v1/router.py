from fastapi import APIRouter
from .endpoints import auth, query, health

api_router = APIRouter()

# 엔드포인트 등록
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(health.router, prefix="/health", tags=["health"])