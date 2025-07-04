from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.api.v1.endpoints.auth import get_current_user
from app.services.text_to_sql import text_to_sql_engine
from app.services.rag_engine import rag_engine
from app.services.langgraph_agent import langgraph_agent
from app.services.langchain_rag import langchain_rag_engine
from app.services.langchain_sql import langchain_sql_engine
from app.services.langserve_server import langserve_server

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    context: Optional[str] = None
    method: Optional[str] = "langgraph"  # langgraph, langchain, original


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
    method: Optional[str] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """자연어 질의 처리 (다중 엔진 지원)"""
    try:
        method = request.method or "langgraph"
        
        if method == "langgraph":
            # LangGraph 에이전트 사용
            result = await langgraph_agent.process_question(request.question)
            
            answer = result["answer"]
            if not result["success"] and result.get("error"):
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
                error=result.get("error"),
                method="langgraph",
                intermediate_steps=result.get("intermediate_steps")
            )
            
        elif method == "langchain":
            # LangChain SQL 엔진 사용
            result = await langchain_sql_engine.process_question_advanced(
                question=request.question,
                method="chain"
            )
            
            return QueryResponse(
                success=result["success"],
                question=result["question"],
                answer=result["answer"],
                sql_query=result.get("sql_query"),
                data=result.get("data"),
                columns=result.get("columns"),
                row_count=result.get("row_count"),
                explanation=result.get("explanation"),
                confidence=0.8 if result["success"] else 0.3,
                error=result.get("error"),
                method="langchain"
            )
            
        else:  # original
            # 기존 Text-to-SQL 엔진 사용
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
                error=result.get("error"),
                method="original"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(current_user: dict = Depends(get_current_user)):
    """질의 히스토리 조회"""
    return {"history": [], "message": "질의 히스토리 기능은 향후 구현 예정입니다."}


@router.post("/initialize")
async def initialize_knowledge_base(current_user: dict = Depends(get_current_user)):
    """지식 베이스 초기화 (LangChain RAG 포함)"""
    try:
        # 기존 RAG 엔진 초기화
        await rag_engine.initialize_knowledge_base()
        
        # LangChain RAG 엔진 초기화
        await langchain_rag_engine.initialize_knowledge_base()
        
        return {"message": "모든 지식 베이스가 성공적으로 초기화되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """벡터 DB 통계 조회"""
    try:
        # 기존 RAG 엔진 통계
        original_stats = await rag_engine.get_collection_stats()
        
        # LangChain RAG 엔진 통계
        langchain_stats = await langchain_rag_engine.get_stats()
        
        # LangChain SQL 엔진 통계
        sql_stats = await langchain_sql_engine.get_stats()
        
        return {
            "original_rag": original_stats,
            "langchain_rag": langchain_stats,
            "langchain_sql": sql_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langserve/agent")
async def langserve_agent_invoke(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """LangServe 에이전트 직접 호출"""
    try:
        result = await langserve_server.invoke_agent(request.question, request.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langserve/rag")
async def langserve_rag_invoke(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """LangServe RAG 직접 호출"""
    try:
        result = await langserve_server.invoke_rag(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langserve/sql")
async def langserve_sql_invoke(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """LangServe SQL 직접 호출"""
    try:
        result = await langserve_server.invoke_sql(request.question, request.method or "manual")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))