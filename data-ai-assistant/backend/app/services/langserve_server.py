from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from langserve import add_routes
from langchain.schema.runnable import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.langgraph_agent import langgraph_agent
from app.services.langchain_rag import langchain_rag_engine
from app.services.langchain_sql import langchain_sql_engine
import logging
import asyncio

logger = logging.getLogger(__name__)


# Pydantic 모델 정의
class QuestionInput(BaseModel):
    """질문 입력 모델"""
    question: str = Field(description="사용자 질문")
    context: Optional[str] = Field(default=None, description="추가 컨텍스트")
    method: Optional[str] = Field(default="agent", description="처리 방법: agent, rag, sql")


class QuestionOutput(BaseModel):
    """질문 출력 모델"""
    success: bool
    answer: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    method: str
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


class RAGInput(BaseModel):
    """RAG 입력 모델"""
    question: str = Field(description="RAG 질문")


class RAGOutput(BaseModel):
    """RAG 출력 모델"""
    answer: str
    source_documents: List[Dict[str, Any]]


class SQLInput(BaseModel):
    """SQL 입력 모델"""
    question: str = Field(description="SQL 변환할 질문")
    method: Optional[str] = Field(default="manual", description="SQL 생성 방법")


class SQLOutput(BaseModel):
    """SQL 출력 모델"""
    sql_query: Optional[str]
    data: Optional[List[Dict[str, Any]]]
    columns: Optional[List[str]]
    success: bool
    error: Optional[str]


class LangServeServer:
    """LangServe 기반 체인 서버"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            temperature=0.1
        )
        
        # 체인들 생성
        self.agent_chain = self._create_agent_chain()
        self.rag_chain = self._create_rag_chain()
        self.sql_chain = self._create_sql_chain()
        self.simple_chat_chain = self._create_simple_chat_chain()
    
    def _create_agent_chain(self) -> RunnableLambda:
        """LangGraph 에이전트 체인"""
        async def agent_runner(input_data: QuestionInput) -> QuestionOutput:
            try:
                result = await langgraph_agent.process_question(input_data.question)
                return QuestionOutput(
                    success=result["success"],
                    answer=result["answer"],
                    sql_query=result.get("sql_query"),
                    data=result.get("data"),
                    confidence=result.get("confidence"),
                    method="langgraph_agent",
                    intermediate_steps=result.get("intermediate_steps")
                )
            except Exception as e:
                logger.error(f"Agent chain error: {str(e)}")
                return QuestionOutput(
                    success=False,
                    answer=f"에이전트 처리 중 오류: {str(e)}",
                    method="langgraph_agent"
                )
        
        return RunnableLambda(agent_runner)
    
    def _create_rag_chain(self) -> RunnableLambda:
        """RAG 체인"""
        async def rag_runner(input_data: RAGInput) -> RAGOutput:
            try:
                result = await langchain_rag_engine.ask_question(input_data.question)
                return RAGOutput(
                    answer=result["answer"],
                    source_documents=result["source_documents"]
                )
            except Exception as e:
                logger.error(f"RAG chain error: {str(e)}")
                return RAGOutput(
                    answer=f"RAG 처리 중 오류: {str(e)}",
                    source_documents=[]
                )
        
        return RunnableLambda(rag_runner)
    
    def _create_sql_chain(self) -> RunnableLambda:
        """SQL 체인"""
        async def sql_runner(input_data: SQLInput) -> SQLOutput:
            try:
                result = await langchain_sql_engine.process_question_advanced(
                    input_data.question, 
                    method=input_data.method
                )
                return SQLOutput(
                    sql_query=result.get("sql_query"),
                    data=result.get("data"),
                    columns=result.get("columns"),
                    success=result["success"],
                    error=result.get("error")
                )
            except Exception as e:
                logger.error(f"SQL chain error: {str(e)}")
                return SQLOutput(
                    sql_query=None,
                    data=None,
                    columns=None,
                    success=False,
                    error=str(e)
                )
        
        return RunnableLambda(sql_runner)
    
    def _create_simple_chat_chain(self) -> RunnableLambda:
        """간단한 채팅 체인"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 도움이 되는 AI 어시스턴트입니다. 
            사용자의 질문에 친절하고 정확하게 답변하세요.
            데이터 관련 질문이 아닌 경우, 일반적인 대화로 응답하세요."""),
            ("human", "{question}")
        ])
        
        def chat_runner(input_data: Dict[str, str]) -> Dict[str, str]:
            try:
                chain = prompt | self.llm
                result = chain.invoke({"question": input_data["question"]})
                return {
                    "answer": result.content,
                    "type": "general_chat"
                }
            except Exception as e:
                logger.error(f"Chat chain error: {str(e)}")
                return {
                    "answer": f"채팅 처리 중 오류: {str(e)}",
                    "type": "error"
                }
        
        return RunnableLambda(chat_runner)
    
    def add_routes_to_app(self, app: FastAPI):
        """FastAPI 앱에 LangServe 라우트 추가"""
        try:
            # 메인 에이전트 체인
            add_routes(
                app,
                self.agent_chain.with_types(input_type=QuestionInput, output_type=QuestionOutput),
                path="/agent",
                enabled_endpoints=["invoke", "batch", "stream"],
            )
            
            # RAG 체인
            add_routes(
                app,
                self.rag_chain.with_types(input_type=RAGInput, output_type=RAGOutput),
                path="/rag",
                enabled_endpoints=["invoke", "batch"],
            )
            
            # SQL 체인
            add_routes(
                app,
                self.sql_chain.with_types(input_type=SQLInput, output_type=SQLOutput),
                path="/sql",
                enabled_endpoints=["invoke", "batch"],
            )
            
            # 간단한 채팅 체인
            add_routes(
                app,
                self.simple_chat_chain,
                path="/chat",
                enabled_endpoints=["invoke", "stream"],
            )
            
            logger.info("LangServe routes added successfully")
            
        except Exception as e:
            logger.error(f"Error adding LangServe routes: {str(e)}")
            raise
    
    async def invoke_agent(self, question: str, context: Optional[str] = None) -> QuestionOutput:
        """에이전트 직접 호출"""
        input_data = QuestionInput(question=question, context=context)
        return await self.agent_chain.ainvoke(input_data)
    
    async def invoke_rag(self, question: str) -> RAGOutput:
        """RAG 직접 호출"""
        input_data = RAGInput(question=question)
        return await self.rag_chain.ainvoke(input_data)
    
    async def invoke_sql(self, question: str, method: str = "manual") -> SQLOutput:
        """SQL 직접 호출"""
        input_data = SQLInput(question=question, method=method)
        return await self.sql_chain.ainvoke(input_data)
    
    def invoke_chat(self, question: str) -> Dict[str, str]:
        """채팅 직접 호출"""
        return self.simple_chat_chain.invoke({"question": question})


# 전역 LangServe 서버 인스턴스
langserve_server = LangServeServer()