from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.api.v1.endpoints.auth import get_current_user
from app.services.text_to_sql import text_to_sql_engine
from app.services.rag_engine import rag_engine

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    context: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    question: str
    answer: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """자연어 질의 처리"""
    try:
        # Text-to-SQL 엔진을 통해 질문 처리
        result = await text_to_sql_engine.process_question(
            question=request.question,
            user_context=request.context
        )
        
        # 응답 생성
        if result["success"]:
            answer = f"질문: {request.question}\n\n"
            if result.get("data"):
                answer += f"총 {result['row_count']}개의 결과를 찾았습니다.\n\n"
                if result["explanation"]:
                    answer += f"설명: {result['explanation']}"
            else:
                answer += "결과를 찾을 수 없습니다."
        else:
            answer = f"죄송합니다. '{request.question}'에 대한 답변을 생성할 수 없습니다."
            if result.get("error"):
                answer += f"\n오류: {result['error']}"
        
        return QueryResponse(
            success=result["success"],
            question=result["question"],
            answer=answer,
            sql_query=result.get("sql_query"),
            data=result.get("data"),
            columns=result.get("columns"),
            row_count=result.get("row_count"),
            explanation=result.get("explanation"),
            confidence=result.get("confidence"),
            error=result.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(current_user: dict = Depends(get_current_user)):
    """질의 히스토리 조회"""
    return {"history": [], "message": "질의 히스토리 기능은 향후 구현 예정입니다."}


@router.post("/initialize")
async def initialize_knowledge_base(current_user: dict = Depends(get_current_user)):
    """지식 베이스 초기화"""
    try:
        await rag_engine.initialize_knowledge_base()
        return {"message": "지식 베이스가 성공적으로 초기화되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """벡터 DB 통계 조회"""
    try:
        stats = await rag_engine.get_collection_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))