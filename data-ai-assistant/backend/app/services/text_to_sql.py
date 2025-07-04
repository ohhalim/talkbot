import openai
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.rag_engine import rag_engine
import logging
import json
import re

logger = logging.getLogger(__name__)


class TextToSQLEngine:
    """Text-to-SQL 변환 엔진"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.engine = create_engine(settings.DATABASE_URL)
        self.rag_engine = rag_engine
    
    async def generate_sql(self, question: str, user_context: Optional[str] = None) -> Dict[str, Any]:
        """자연어 질문을 SQL로 변환"""
        try:
            # 1. RAG를 통해 관련 컨텍스트 검색
            context = await self.rag_engine.search_relevant_context(question, top_k=3)
            
            # 2. 프롬프트 생성
            prompt = await self._build_prompt(question, context, user_context)
            
            # 3. OpenAI API 호출
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # 4. 응답 파싱
            result = self._parse_response(response.choices[0].message.content)
            
            # 5. SQL 검증
            if result.get("sql_query"):
                validation_result = await self._validate_sql(result["sql_query"])
                result.update(validation_result)
            
            return result
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "error": str(e),
                "sql_query": None,
                "explanation": "SQL 생성 중 오류가 발생했습니다."
            }
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return """
        당신은 데이터베이스 전문가입니다. 사용자의 자연어 질문을 PostgreSQL 쿼리로 변환해주세요.
        
        규칙:
        1. SELECT 문만 생성하세요 (INSERT, UPDATE, DELETE 금지)
        2. 안전한 쿼리만 생성하세요
        3. 가능한 한 정확하고 효율적인 쿼리를 작성하세요
        4. 테이블과 컬럼명은 정확히 사용하세요
        5. 응답은 JSON 형식으로 해주세요
        
        응답 형식:
        {
            "sql_query": "SELECT * FROM table_name;",
            "explanation": "쿼리에 대한 설명",
            "confidence": 0.9,
            "tables_used": ["table1", "table2"]
        }
        """
    
    async def _build_prompt(self, question: str, context: Dict[str, Any], user_context: Optional[str] = None) -> str:
        """프롬프트 생성"""
        prompt = f"질문: {question}\n\n"
        
        # 테이블 스키마 정보 추가
        if context.get("table_schemas"):
            prompt += "사용 가능한 테이블 정보:\n"
            for schema in context["table_schemas"][:2]:  # 상위 2개만 사용
                prompt += f"{schema['document']}\n\n"
        
        # 비즈니스 용어 정보 추가
        if context.get("business_terms"):
            prompt += "관련 비즈니스 용어:\n"
            for term in context["business_terms"][:3]:  # 상위 3개만 사용
                prompt += f"{term['document']}\n"
        
        # SQL 예시 추가
        if context.get("sql_examples"):
            prompt += "\n참고할 만한 SQL 예시:\n"
            for example in context["sql_examples"][:2]:  # 상위 2개만 사용
                prompt += f"{example['document']}\n\n"
        
        # 사용자 컨텍스트 추가
        if user_context:
            prompt += f"\n추가 컨텍스트: {user_context}\n"
        
        prompt += "\n위 정보를 바탕으로 질문에 대한 SQL 쿼리를 생성해주세요."
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """응답 파싱"""
        try:
            # JSON 응답 파싱 시도
            if response_text.strip().startswith('{'):
                return json.loads(response_text)
            
            # JSON이 아닌 경우 SQL 추출 시도
            sql_match = re.search(r'```sql\n(.*?)\n```', response_text, re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1).strip()
                return {
                    "sql_query": sql_query,
                    "explanation": "SQL 쿼리를 추출했습니다.",
                    "confidence": 0.7,
                    "tables_used": self._extract_tables_from_sql(sql_query)
                }
            
            # 기본 응답
            return {
                "sql_query": None,
                "explanation": "SQL 쿼리를 생성할 수 없습니다.",
                "confidence": 0.0,
                "error": "응답 파싱 실패"
            }
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return {
                "sql_query": None,
                "explanation": "응답 파싱 중 오류가 발생했습니다.",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _extract_tables_from_sql(self, sql_query: str) -> List[str]:
        """SQL에서 테이블명 추출"""
        try:
            # 간단한 정규식으로 테이블명 추출
            tables = re.findall(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
            tables += re.findall(r'JOIN\s+(\w+)', sql_query, re.IGNORECASE)
            return list(set(tables))
        except Exception:
            return []
    
    async def _validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """SQL 쿼리 검증"""
        try:
            # 1. 기본 안전성 검사
            if not self._is_safe_query(sql_query):
                return {
                    "is_valid": False,
                    "error": "안전하지 않은 쿼리입니다."
                }
            
            # 2. 구문 검사 (EXPLAIN으로 테스트)
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
            'truncate', 'grant', 'revoke', 'exec', 'execute'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in sql_lower:
                return False
        
        # SELECT로 시작하는지 확인
        if not sql_lower.startswith('select'):
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
            
            # LIMIT 추가 (안전장치)
            if 'limit' not in sql_query.lower():
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit};"
            
            # 쿼리 실행
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                
                # 결과 포맷팅
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
    
    async def process_question(self, question: str, user_context: Optional[str] = None) -> Dict[str, Any]:
        """질문 전체 처리 파이프라인"""
        try:
            # 1. SQL 생성
            sql_result = await self.generate_sql(question, user_context)
            
            if sql_result.get("error") or not sql_result.get("sql_query"):
                return {
                    "success": False,
                    "question": question,
                    "error": sql_result.get("error", "SQL 생성 실패"),
                    "sql_query": None,
                    "data": None,
                    "explanation": sql_result.get("explanation")
                }
            
            # 2. SQL 실행
            if sql_result.get("is_valid", True):
                execution_result = await self.execute_sql(sql_result["sql_query"])
                
                return {
                    "success": execution_result["success"],
                    "question": question,
                    "sql_query": sql_result["sql_query"],
                    "data": execution_result.get("data"),
                    "columns": execution_result.get("columns"),
                    "row_count": execution_result.get("row_count"),
                    "explanation": sql_result.get("explanation"),
                    "confidence": sql_result.get("confidence"),
                    "error": execution_result.get("error")
                }
            else:
                return {
                    "success": False,
                    "question": question,
                    "sql_query": sql_result["sql_query"],
                    "error": sql_result.get("error"),
                    "explanation": sql_result.get("explanation"),
                    "data": None
                }
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "sql_query": None,
                "data": None,
                "explanation": "질문 처리 중 오류가 발생했습니다."
            }


# 전역 Text-to-SQL 엔진 인스턴스
text_to_sql_engine = TextToSQLEngine()