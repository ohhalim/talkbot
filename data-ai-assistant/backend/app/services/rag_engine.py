from typing import List, Dict, Any, Optional
from app.services.vector_store import vector_store
from app.services.embedding import embedding_service
from app.services.database_introspection import db_introspection
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG (Retrieval-Augmented Generation) 엔진"""
    
    def __init__(self):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.db_introspection = db_introspection
    
    async def initialize_knowledge_base(self):
        """지식 베이스 초기화"""
        try:
            # 1. 테이블 스키마 정보 수집 및 저장
            await self._index_table_schemas()
            
            # 2. 기본 비즈니스 용어 저장
            await self._index_business_terms()
            
            # 3. SQL 예시 저장
            await self._index_sql_examples()
            
            logger.info("Knowledge base initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {str(e)}")
            raise
    
    async def _index_table_schemas(self):
        """테이블 스키마 정보 인덱싱"""
        try:
            tables = self.db_introspection.get_all_tables()
            
            documents = []
            metadatas = []
            ids = []
            
            for table_name in tables:
                # 시스템 테이블 제외
                if table_name.startswith('pg_') or table_name in ['information_schema']:
                    continue
                
                description = self.db_introspection.generate_table_description(table_name)
                schema = self.db_introspection.get_table_schema(table_name)
                
                documents.append(description)
                metadatas.append({
                    "type": "table_schema",
                    "table_name": table_name,
                    "column_count": len(schema["columns"]),
                    "has_foreign_keys": len(schema["foreign_keys"]) > 0
                })
                ids.append(f"table_{table_name}")
            
            if documents:
                await self.vector_store.add_documents(
                    collection_name="table_schemas",
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Indexed {len(documents)} table schemas")
        except Exception as e:
            logger.error(f"Error indexing table schemas: {str(e)}")
            raise
    
    async def _index_business_terms(self):
        """비즈니스 용어 인덱싱"""
        business_terms = [
            {
                "term": "고객",
                "definition": "제품이나 서비스를 구매하는 개인 또는 기업",
                "category": "business",
                "examples": "customers 테이블의 데이터"
            },
            {
                "term": "주문",
                "definition": "고객이 제품을 구매하는 거래",
                "category": "business",
                "examples": "orders 테이블의 데이터"
            },
            {
                "term": "제품",
                "definition": "판매되는 상품이나 서비스",
                "category": "business",
                "examples": "products 테이블의 데이터"
            },
            {
                "term": "매출",
                "definition": "판매로 인한 수익 금액",
                "category": "finance",
                "examples": "orders 테이블의 total_amount 컬럼"
            },
            {
                "term": "재고",
                "definition": "판매 가능한 제품의 수량",
                "category": "inventory",
                "examples": "products 테이블의 stock_quantity 컬럼"
            }
        ]
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for term_data in business_terms:
                document = f"용어: {term_data['term']}\n정의: {term_data['definition']}\n예시: {term_data['examples']}"
                documents.append(document)
                metadatas.append({
                    "type": "business_term",
                    "term": term_data["term"],
                    "category": term_data["category"]
                })
                ids.append(f"term_{term_data['term']}")
            
            await self.vector_store.add_documents(
                collection_name="business_terms",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(documents)} business terms")
        except Exception as e:
            logger.error(f"Error indexing business terms: {str(e)}")
            raise
    
    async def _index_sql_examples(self):
        """SQL 예시 인덱싱"""
        sql_examples = [
            {
                "question": "모든 고객 목록을 보여주세요",
                "sql": "SELECT * FROM customers ORDER BY created_at DESC;",
                "explanation": "customers 테이블의 모든 레코드를 최신 순으로 조회",
                "complexity": "simple"
            },
            {
                "question": "총 주문 금액이 가장 높은 고객을 찾아주세요",
                "sql": "SELECT c.name, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.name ORDER BY total_spent DESC LIMIT 1;",
                "explanation": "고객별 총 주문 금액을 계산하여 가장 많이 구매한 고객 조회",
                "complexity": "medium"
            },
            {
                "question": "카테고리별 제품 수량을 보여주세요",
                "sql": "SELECT category, COUNT(*) as product_count FROM products GROUP BY category ORDER BY product_count DESC;",
                "explanation": "제품을 카테고리별로 그룹화하여 각 카테고리의 제품 수 조회",
                "complexity": "simple"
            },
            {
                "question": "재고가 부족한 제품을 찾아주세요",
                "sql": "SELECT name, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC;",
                "explanation": "재고가 10개 미만인 제품들을 재고 수량 순으로 조회",
                "complexity": "simple"
            }
        ]
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for i, example in enumerate(sql_examples):
                document = f"질문: {example['question']}\nSQL: {example['sql']}\n설명: {example['explanation']}"
                documents.append(document)
                metadatas.append({
                    "type": "sql_example",
                    "complexity": example["complexity"],
                    "question": example["question"]
                })
                ids.append(f"sql_example_{i}")
            
            await self.vector_store.add_documents(
                collection_name="sql_examples",
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(documents)} SQL examples")
        except Exception as e:
            logger.error(f"Error indexing SQL examples: {str(e)}")
            raise
    
    async def search_relevant_context(self, question: str, top_k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """질문과 관련된 컨텍스트 검색"""
        try:
            results = {}
            
            # 1. 테이블 스키마 검색
            table_results = await self.vector_store.search_similar(
                collection_name="table_schemas",
                query_text=question,
                n_results=top_k
            )
            results["table_schemas"] = table_results
            
            # 2. 비즈니스 용어 검색
            term_results = await self.vector_store.search_similar(
                collection_name="business_terms",
                query_text=question,
                n_results=top_k
            )
            results["business_terms"] = term_results
            
            # 3. SQL 예시 검색
            sql_results = await self.vector_store.search_similar(
                collection_name="sql_examples",
                query_text=question,
                n_results=top_k
            )
            results["sql_examples"] = sql_results
            
            logger.info(f"Retrieved context for question: {question}")
            return results
        except Exception as e:
            logger.error(f"Error searching relevant context: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 조회"""
        try:
            stats = {}
            for collection_name in ["table_schemas", "business_terms", "sql_examples"]:
                stats[collection_name] = await self.vector_store.get_collection_stats(collection_name)
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise


# 전역 RAG 엔진 인스턴스
rag_engine = RAGEngine()