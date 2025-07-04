from typing import Dict, Any, List, Optional
from langchain.chains import create_sql_query_chain
from langchain_experimental.sql import SQLDatabaseChain
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from langchain.memory import ConversationBufferMemory
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.langchain_rag import langchain_rag_engine
import logging
import re
import json

logger = logging.getLogger(__name__)


class SQLQueryParser(BaseOutputParser):
    """SQL 쿼리 파싱을 위한 커스텀 파서"""
    
    def parse(self, text: str) -> str:
        # SQL 쿼리 추출
        sql_match = re.search(r'```sql\n(.*?)\n```', text, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # SQL로 시작하는 라인 찾기
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SELECT'):
                return line
        
        return text.strip()


class LangChainSQLEngine:
    """LangChain 기반 Text-to-SQL 엔진"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            temperature=0
        )
        
        # SQLDatabase 연결
        self.engine = create_engine(settings.DATABASE_URL)
        self.db = SQLDatabase(self.engine)
        
        # 메모리
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.rag_engine = langchain_rag_engine
        self._setup_chains()
    
    def _setup_chains(self):
        """체인 설정"""
        # SQL 생성 체인
        self.sql_chain = create_sql_query_chain(
            llm=self.llm,
            db=self.db,
            prompt=self._get_sql_prompt()
        )
        
        # SQL 실행 체인
        self.sql_execute_chain = SQLDatabaseChain.from_llm(
            llm=self.llm,
            db=self.db,
            verbose=True,
            use_query_checker=True,
            return_intermediate_steps=True
        )
        
        # SQL 에이전트 (고급 기능용)
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        self.sql_agent = create_sql_agent(
            llm=self.llm,
            toolkit=toolkit,
            verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
    
    def _get_sql_prompt(self) -> PromptTemplate:
        """SQL 생성을 위한 프롬프트 템플릿"""
        template = """
주어진 입력에 대해 PostgreSQL 쿼리를 작성하세요.

사용 가능한 테이블과 스키마:
{table_info}

관련 컨텍스트:
{context}

다음 규칙을 따르세요:
1. SELECT 문만 사용하세요 (INSERT, UPDATE, DELETE 금지)
2. 테이블과 컬럼명을 정확히 사용하세요
3. PostgreSQL 문법을 사용하세요
4. LIMIT을 사용하여 결과를 제한하세요 (기본 100개)
5. 안전한 쿼리만 작성하세요

질문: {input}
SQL 쿼리:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["input", "table_info", "context"]
        )
    
    async def generate_sql(self, question: str, use_rag: bool = True) -> Dict[str, Any]:
        """SQL 쿼리 생성"""
        try:
            context = ""
            if use_rag:
                # RAG를 통한 컨텍스트 검색
                relevant_docs = await self.rag_engine.get_relevant_context(question, k=3)
                context = "\n\n".join([doc["content"] for doc in relevant_docs])
            
            # SQL 생성
            sql_query = self.sql_chain.invoke({
                "question": question,
                "context": context
            })
            
            # SQL 검증
            validation_result = await self._validate_sql(sql_query)
            
            return {
                "sql_query": sql_query,
                "context": context,
                "is_valid": validation_result["is_valid"],
                "validation_error": validation_result.get("error"),
                "explanation": "LangChain을 사용하여 생성된 SQL 쿼리입니다."
            }
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "sql_query": None,
                "error": str(e),
                "is_valid": False
            }
    
    async def execute_sql_with_chain(self, question: str) -> Dict[str, Any]:
        """SQL 체인을 사용한 실행"""
        try:
            result = self.sql_execute_chain.invoke({
                "query": question
            })
            
            return {
                "success": True,
                "answer": result["result"],
                "sql_query": result.get("intermediate_steps", [{}])[-1].get("sql_cmd"),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            logger.error(f"Error executing SQL with chain: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "answer": f"SQL 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def ask_with_agent(self, question: str) -> Dict[str, Any]:
        """SQL 에이전트를 사용한 질의"""
        try:
            result = self.sql_agent.invoke({
                "input": question
            })
            
            return {
                "success": True,
                "answer": result["output"],
                "intermediate_steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            logger.error(f"Error with SQL agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "answer": f"SQL 에이전트 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def _validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """SQL 쿼리 검증"""
        try:
            # 기본 안전성 검사
            if not self._is_safe_query(sql_query):
                return {
                    "is_valid": False,
                    "error": "안전하지 않은 쿼리입니다."
                }
            
            # 구문 검사
            with self.engine.connect() as conn:
                conn.execute(text(f"EXPLAIN {sql_query}"))
            
            return {
                "is_valid": True,
                "error": None
            }
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"SQL 검증 실패: {str(e)}"
            }
    
    def _is_safe_query(self, sql_query: str) -> bool:
        """쿼리 안전성 검사"""
        sql_lower = sql_query.lower().strip()
        
        # 금지된 키워드 검사
        forbidden_keywords = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'grant', 'revoke', 'exec', 'execute', 'call'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in sql_lower:
                return False
        
        # SELECT로 시작하는지 확인
        if not sql_lower.startswith('select') and 'select' not in sql_lower:
            return False
        
        return True
    
    async def execute_sql(self, sql_query: str, limit: int = 100) -> Dict[str, Any]:
        """SQL 실행"""
        try:
            # 안전성 검사
            if not self._is_safe_query(sql_query):
                return {
                    "success": False,
                    "error": "안전하지 않은 쿼리입니다.",
                    "data": None
                }
            
            # LIMIT 추가
            if 'limit' not in sql_query.lower():
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit};"
            
            # 쿼리 실행
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                
                data = [
                    {col: str(row[i]) if row[i] is not None else None 
                     for i, col in enumerate(columns)}
                    for row in rows
                ]
                
                return {
                    "success": True,
                    "data": data,
                    "columns": columns,
                    "row_count": len(data),
                    "error": None
                }
        except Exception as e:
            logger.error(f"Error executing SQL: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def process_question_advanced(
        self, 
        question: str, 
        method: str = "chain"  # "chain", "agent", "manual"
    ) -> Dict[str, Any]:
        """고급 질문 처리"""
        try:
            if method == "agent":
                # SQL 에이전트 사용
                result = await self.ask_with_agent(question)
                return {
                    "success": result["success"],
                    "question": question,
                    "answer": result["answer"],
                    "method": "agent",
                    "error": result.get("error")
                }
            
            elif method == "chain":
                # SQL 체인 사용
                result = await self.execute_sql_with_chain(question)
                return {
                    "success": result["success"],
                    "question": question,
                    "answer": result["answer"],
                    "sql_query": result.get("sql_query"),
                    "method": "chain",
                    "error": result.get("error")
                }
            
            else:  # manual
                # 수동 SQL 생성 후 실행
                sql_result = await self.generate_sql(question)
                
                if not sql_result.get("is_valid"):
                    return {
                        "success": False,
                        "question": question,
                        "error": sql_result.get("validation_error"),
                        "method": "manual"
                    }
                
                exec_result = await self.execute_sql(sql_result["sql_query"])
                
                return {
                    "success": exec_result["success"],
                    "question": question,
                    "sql_query": sql_result["sql_query"],
                    "data": exec_result.get("data"),
                    "columns": exec_result.get("columns"),
                    "row_count": exec_result.get("row_count"),
                    "explanation": sql_result.get("explanation"),
                    "method": "manual",
                    "error": exec_result.get("error")
                }
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "method": method
            }
    
    def get_schema_info(self) -> str:
        """스키마 정보 조회"""
        try:
            return self.db.get_table_info()
        except Exception as e:
            logger.error(f"Error getting schema info: {str(e)}")
            return "스키마 정보를 가져올 수 없습니다."
    
    def get_table_names(self) -> List[str]:
        """테이블 이름 목록 조회"""
        try:
            return self.db.get_usable_table_names()
        except Exception as e:
            logger.error(f"Error getting table names: {str(e)}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """통계 정보"""
        try:
            table_names = self.get_table_names()
            schema_info = self.get_schema_info()
            
            return {
                "total_tables": len(table_names),
                "table_names": table_names,
                "database_type": "PostgreSQL",
                "langchain_version": "enabled",
                "schema_info_length": len(schema_info)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}


# 전역 LangChain SQL 엔진 인스턴스
langchain_sql_engine = LangChainSQLEngine()