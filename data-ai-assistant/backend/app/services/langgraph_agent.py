from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.langchain_rag import langchain_rag_engine
import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """에이전트 상태 정의"""
    messages: Annotated[List[BaseMessage], "대화 메시지 리스트"]
    question: str
    sql_query: Optional[str]
    sql_result: Optional[Dict[str, Any]]
    context: Optional[str]
    analysis_type: Optional[str]  # "simple", "complex", "analytical"
    confidence: float
    error: Optional[str]
    final_answer: Optional[str]
    intermediate_steps: List[Dict[str, Any]]


class DataAnalysisAgent:
    """LangGraph 기반 데이터 분석 에이전트"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            temperature=0.1
        )
        
        # 데이터베이스 연결
        self.engine = create_engine(settings.DATABASE_URL)
        self.db = SQLDatabase(self.engine)
        
        # RAG 엔진
        self.rag_engine = langchain_rag_engine
        
        # 도구 설정
        self.tools = self._create_tools()
        self.tool_executor = ToolExecutor(self.tools)
        
        # 그래프 구성
        self.graph = self._create_graph()
    
    def _create_tools(self) -> List[Tool]:
        """에이전트가 사용할 도구들 생성"""
        tools = [
            Tool(
                name="get_table_schema",
                description="데이터베이스 테이블 스키마 정보를 가져옵니다",
                func=self._get_table_schema
            ),
            Tool(
                name="execute_sql",
                description="안전한 SELECT SQL 쿼리를 실행합니다",
                func=self._execute_sql_tool
            ),
            Tool(
                name="search_context",
                description="RAG를 통해 관련 컨텍스트를 검색합니다",
                func=self._search_context_tool
            ),
            Tool(
                name="validate_sql",
                description="SQL 쿼리의 안전성을 검증합니다",
                func=self._validate_sql_tool
            ),
            Tool(
                name="analyze_data",
                description="쿼리 결과를 분석하고 인사이트를 제공합니다",
                func=self._analyze_data_tool
            )
        ]
        return tools
    
    def _get_table_schema(self, table_name: str = "") -> str:
        """테이블 스키마 정보 조회"""
        try:
            if table_name:
                return self.db.get_table_info([table_name])
            else:
                return self.db.get_table_info()
        except Exception as e:
            return f"스키마 조회 오류: {str(e)}"
    
    def _execute_sql_tool(self, sql_query: str) -> str:
        """SQL 실행 도구"""
        try:
            result = self._execute_sql_safe(sql_query)
            if result["success"]:
                return json.dumps({
                    "success": True,
                    "data": result["data"][:10],  # 처음 10개 행만
                    "row_count": result["row_count"],
                    "columns": result["columns"]
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": result["error"]
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    
    def _search_context_tool(self, question: str) -> str:
        """컨텍스트 검색 도구"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            context_docs = loop.run_until_complete(
                self.rag_engine.get_relevant_context(question, k=3)
            )
            
            context = "\n\n".join([doc["content"] for doc in context_docs])
            return context
        except Exception as e:
            return f"컨텍스트 검색 오류: {str(e)}"
    
    def _validate_sql_tool(self, sql_query: str) -> str:
        """SQL 검증 도구"""
        try:
            if self._is_safe_query(sql_query):
                # 구문 검증
                with self.engine.connect() as conn:
                    conn.execute(text(f"EXPLAIN {sql_query}"))
                return "SQL 쿼리가 안전하고 유효합니다."
            else:
                return "SQL 쿼리가 안전하지 않습니다."
        except Exception as e:
            return f"SQL 검증 오류: {str(e)}"
    
    def _analyze_data_tool(self, data_json: str) -> str:
        """데이터 분석 도구"""
        try:
            data = json.loads(data_json)
            if not data.get("success"):
                return "분석할 데이터가 없습니다."
            
            rows = data.get("data", [])
            columns = data.get("columns", [])
            
            if not rows:
                return "데이터가 비어있습니다."
            
            analysis = []
            analysis.append(f"총 {len(rows)}개의 레코드가 조회되었습니다.")
            analysis.append(f"컬럼: {', '.join(columns)}")
            
            # 숫자 컬럼 분석
            numeric_cols = []
            for col in columns:
                if rows and rows[0].get(col) and str(rows[0][col]).replace('.', '').replace('-', '').isdigit():
                    numeric_cols.append(col)
            
            if numeric_cols:
                analysis.append(f"숫자 컬럼: {', '.join(numeric_cols)}")
            
            return "\n".join(analysis)
        except Exception as e:
            return f"데이터 분석 오류: {str(e)}"
    
    def _create_graph(self) -> StateGraph:
        """LangGraph 구성"""
        graph = StateGraph(AgentState)
        
        # 노드 추가
        graph.add_node("analyzer", self._analyze_question)
        graph.add_node("context_retriever", self._retrieve_context)
        graph.add_node("sql_generator", self._generate_sql)
        graph.add_node("sql_executor", self._execute_sql)
        graph.add_node("result_analyzer", self._analyze_result)
        graph.add_node("answer_generator", self._generate_answer)
        
        # 엣지 정의
        graph.set_entry_point("analyzer")
        
        graph.add_edge("analyzer", "context_retriever")
        graph.add_edge("context_retriever", "sql_generator")
        graph.add_conditional_edges(
            "sql_generator",
            self._should_execute_sql,
            {
                "execute": "sql_executor",
                "error": "answer_generator"
            }
        )
        graph.add_edge("sql_executor", "result_analyzer")
        graph.add_edge("result_analyzer", "answer_generator")
        graph.add_edge("answer_generator", END)
        
        return graph.compile()
    
    def _analyze_question(self, state: AgentState) -> AgentState:
        """질문 분석"""
        question = state["question"]
        
        # 질문 복잡도 분석
        complexity_prompt = f"""
다음 질문의 복잡도를 분석하고 분류하세요:

질문: {question}

분류 기준:
- simple: 단순한 조회, 기본적인 필터링
- complex: 조인, 그룹화, 집계 함수 필요
- analytical: 고급 분석, 통계, 트렌드 분석

응답은 simple, complex, analytical 중 하나만 반환하세요.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=complexity_prompt)])
            analysis_type = response.content.strip().lower()
            
            if analysis_type not in ["simple", "complex", "analytical"]:
                analysis_type = "simple"
        except:
            analysis_type = "simple"
        
        state["analysis_type"] = analysis_type
        state["intermediate_steps"].append({
            "step": "question_analysis",
            "result": f"질문 복잡도: {analysis_type}",
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    def _retrieve_context(self, state: AgentState) -> AgentState:
        """컨텍스트 검색"""
        question = state["question"]
        
        try:
            import asyncio
            loop = asyncio.new_event_loop() if not asyncio.get_event_loop().is_running() else asyncio.get_event_loop()
            
            if loop.is_running():
                # 이미 실행 중인 루프가 있는 경우
                context_docs = []
            else:
                context_docs = loop.run_until_complete(
                    self.rag_engine.get_relevant_context(question, k=5)
                )
            
            context = "\n\n".join([doc["content"] for doc in context_docs])
            state["context"] = context
            
            state["intermediate_steps"].append({
                "step": "context_retrieval",
                "result": f"관련 문서 {len(context_docs)}개 검색",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Context retrieval error: {str(e)}")
            state["context"] = ""
        
        return state
    
    def _generate_sql(self, state: AgentState) -> AgentState:
        """SQL 생성"""
        question = state["question"]
        context = state.get("context", "")
        analysis_type = state.get("analysis_type", "simple")
        
        # 테이블 스키마 정보
        schema_info = self._get_table_schema()
        
        sql_prompt = f"""
데이터베이스 질의를 위한 PostgreSQL 쿼리를 생성하세요.

질문: {question}
분석 유형: {analysis_type}

데이터베이스 스키마:
{schema_info}

관련 컨텍스트:
{context}

규칙:
1. SELECT 문만 사용 (INSERT, UPDATE, DELETE 금지)
2. 안전한 쿼리만 생성
3. 결과는 100개로 제한 (LIMIT 100)
4. 복잡한 분석의 경우 적절한 집계 함수 사용
5. PostgreSQL 문법 준수

SQL 쿼리만 반환하세요:
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=sql_prompt)])
            sql_query = response.content.strip()
            
            # SQL 쿼리에서 불필요한 텍스트 제거
            sql_query = re.sub(r'^```sql\s*', '', sql_query)
            sql_query = re.sub(r'\s*```$', '', sql_query)
            sql_query = sql_query.strip()
            
            # 안전성 검증
            if self._is_safe_query(sql_query):
                state["sql_query"] = sql_query
                state["error"] = None
            else:
                state["sql_query"] = None
                state["error"] = "안전하지 않은 SQL 쿼리가 생성되었습니다."
            
            state["intermediate_steps"].append({
                "step": "sql_generation",
                "result": f"SQL 생성: {sql_query[:100]}...",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            state["sql_query"] = None
            state["error"] = f"SQL 생성 오류: {str(e)}"
        
        return state
    
    def _should_execute_sql(self, state: AgentState) -> str:
        """SQL 실행 여부 결정"""
        if state.get("sql_query") and not state.get("error"):
            return "execute"
        else:
            return "error"
    
    def _execute_sql(self, state: AgentState) -> AgentState:
        """SQL 실행"""
        sql_query = state["sql_query"]
        
        try:
            result = self._execute_sql_safe(sql_query)
            state["sql_result"] = result
            
            if result["success"]:
                state["confidence"] = 0.9
            else:
                state["confidence"] = 0.3
                state["error"] = result["error"]
            
            state["intermediate_steps"].append({
                "step": "sql_execution",
                "result": f"쿼리 실행: {result['success']}, 행 수: {result.get('row_count', 0)}",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            state["sql_result"] = {"success": False, "error": str(e)}
            state["confidence"] = 0.1
            state["error"] = str(e)
        
        return state
    
    def _analyze_result(self, state: AgentState) -> AgentState:
        """결과 분석"""
        sql_result = state.get("sql_result", {})
        
        if sql_result.get("success"):
            data = sql_result.get("data", [])
            columns = sql_result.get("columns", [])
            
            # 간단한 분석
            analysis = {
                "row_count": len(data),
                "column_count": len(columns),
                "has_data": len(data) > 0
            }
            
            state["intermediate_steps"].append({
                "step": "result_analysis",
                "result": f"데이터 분석: {analysis}",
                "timestamp": datetime.now().isoformat()
            })
        
        return state
    
    def _generate_answer(self, state: AgentState) -> AgentState:
        """최종 답변 생성"""
        question = state["question"]
        sql_query = state.get("sql_query")
        sql_result = state.get("sql_result", {})
        error = state.get("error")
        
        if error:
            state["final_answer"] = f"죄송합니다. 질문 처리 중 오류가 발생했습니다: {error}"
        elif sql_result.get("success"):
            data = sql_result.get("data", [])
            row_count = sql_result.get("row_count", 0)
            
            answer_prompt = f"""
사용자 질문에 대한 답변을 생성하세요.

질문: {question}
실행된 SQL: {sql_query}
결과 행 수: {row_count}

다음 형식으로 답변하세요:
1. 질문에 대한 직접적인 답변
2. 주요 결과 요약
3. 필요시 추가 인사이트

간결하고 명확하게 답변하세요.
"""
            
            try:
                response = self.llm.invoke([HumanMessage(content=answer_prompt)])
                state["final_answer"] = response.content.strip()
            except:
                state["final_answer"] = f"질문에 대한 결과를 찾았습니다. 총 {row_count}개의 결과가 있습니다."
        else:
            state["final_answer"] = "질문에 대한 답변을 찾을 수 없습니다."
        
        state["intermediate_steps"].append({
            "step": "answer_generation",
            "result": "최종 답변 생성 완료",
            "timestamp": datetime.now().isoformat()
        })
        
        return state
    
    def _execute_sql_safe(self, sql_query: str) -> Dict[str, Any]:
        """안전한 SQL 실행"""
        try:
            if not self._is_safe_query(sql_query):
                return {
                    "success": False,
                    "error": "안전하지 않은 쿼리입니다."
                }
            
            # LIMIT 추가
            if 'limit' not in sql_query.lower():
                sql_query = f"{sql_query.rstrip(';')} LIMIT 100;"
            
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
                    "row_count": len(data)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_safe_query(self, sql_query: str) -> bool:
        """쿼리 안전성 검사"""
        sql_lower = sql_query.lower().strip()
        
        forbidden_keywords = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'grant', 'revoke', 'exec', 'execute', 'call'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in sql_lower:
                return False
        
        if not sql_lower.startswith('select') and 'select' not in sql_lower:
            return False
        
        return True
    
    async def process_question(self, question: str) -> Dict[str, Any]:
        """질문 처리 메인 함수"""
        try:
            # 초기 상태 설정
            initial_state = AgentState(
                messages=[HumanMessage(content=question)],
                question=question,
                sql_query=None,
                sql_result=None,
                context=None,
                analysis_type=None,
                confidence=0.0,
                error=None,
                final_answer=None,
                intermediate_steps=[]
            )
            
            # 그래프 실행
            final_state = self.graph.invoke(initial_state)
            
            return {
                "success": not bool(final_state.get("error")),
                "question": question,
                "answer": final_state.get("final_answer"),
                "sql_query": final_state.get("sql_query"),
                "data": final_state.get("sql_result", {}).get("data"),
                "columns": final_state.get("sql_result", {}).get("columns"),
                "row_count": final_state.get("sql_result", {}).get("row_count"),
                "confidence": final_state.get("confidence", 0.0),
                "analysis_type": final_state.get("analysis_type"),
                "intermediate_steps": final_state.get("intermediate_steps", []),
                "error": final_state.get("error")
            }
        except Exception as e:
            logger.error(f"Error in LangGraph agent: {str(e)}")
            return {
                "success": False,
                "question": question,
                "answer": f"처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e)
            }


# 전역 LangGraph 에이전트 인스턴스
langgraph_agent = DataAnalysisAgent()