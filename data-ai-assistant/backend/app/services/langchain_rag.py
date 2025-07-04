from typing import List, Dict, Any, Optional
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from app.core.config import settings
from app.services.database_introspection import db_introspection
import logging
import os

logger = logging.getLogger(__name__)


class LangChainRAGEngine:
    """LangChain 기반 RAG 엔진"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            temperature=0.1
        )
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-ada-002"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        # ChromaDB 설정
        self.persist_directory = settings.CHROMADB_PERSIST_DIRECTORY
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.vectorstore = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """벡터 스토어 초기화"""
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name="data_ai_assistant"
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    async def initialize_knowledge_base(self):
        """지식 베이스 초기화"""
        try:
            documents = []
            
            # 1. 테이블 스키마 문서 생성
            schema_docs = await self._create_schema_documents()
            documents.extend(schema_docs)
            
            # 2. 비즈니스 용어 문서 생성
            term_docs = await self._create_business_term_documents()
            documents.extend(term_docs)
            
            # 3. SQL 예시 문서 생성
            sql_docs = await self._create_sql_example_documents()
            documents.extend(sql_docs)
            
            # 4. 문서를 벡터 스토어에 추가
            if documents:
                # 기존 컬렉션 삭제 후 재생성
                try:
                    self.vectorstore.delete_collection()
                except:
                    pass
                
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                    collection_name="data_ai_assistant"
                )
                
                # 텍스트 분할 및 추가
                split_docs = self.text_splitter.split_documents(documents)
                self.vectorstore.add_documents(split_docs)
                
                logger.info(f"Knowledge base initialized with {len(split_docs)} document chunks")
            
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {str(e)}")
            raise
    
    async def _create_schema_documents(self) -> List[Document]:
        """테이블 스키마 문서 생성"""
        documents = []
        try:
            tables = db_introspection.get_all_tables()
            
            for table_name in tables:
                if table_name.startswith('pg_') or table_name in ['information_schema']:
                    continue
                
                description = db_introspection.generate_table_description(table_name)
                schema = db_introspection.get_table_schema(table_name)
                
                doc = Document(
                    page_content=description,
                    metadata={
                        "type": "table_schema",
                        "table_name": table_name,
                        "column_count": len(schema["columns"]),
                        "source": f"table_{table_name}"
                    }
                )
                documents.append(doc)
            
            logger.info(f"Created {len(documents)} schema documents")
            return documents
        except Exception as e:
            logger.error(f"Error creating schema documents: {str(e)}")
            return []
    
    async def _create_business_term_documents(self) -> List[Document]:
        """비즈니스 용어 문서 생성"""
        business_terms = [
            {
                "term": "고객",
                "definition": "제품이나 서비스를 구매하는 개인 또는 기업",
                "category": "business",
                "examples": "customers 테이블의 데이터",
                "related_tables": ["customers", "orders"]
            },
            {
                "term": "주문",
                "definition": "고객이 제품을 구매하는 거래",
                "category": "business",
                "examples": "orders 테이블의 데이터",
                "related_tables": ["orders", "customers", "products"]
            },
            {
                "term": "제품",
                "definition": "판매되는 상품이나 서비스",
                "category": "business",
                "examples": "products 테이블의 데이터",
                "related_tables": ["products", "orders"]
            },
            {
                "term": "매출",
                "definition": "판매로 인한 수익 금액",
                "category": "finance",
                "examples": "orders 테이블의 total_amount 컬럼",
                "related_tables": ["orders"]
            },
            {
                "term": "재고",
                "definition": "판매 가능한 제품의 수량",
                "category": "inventory",
                "examples": "products 테이블의 stock_quantity 컬럼",
                "related_tables": ["products"]
            }
        ]
        
        documents = []
        for term_data in business_terms:
            content = f"""
용어: {term_data['term']}
정의: {term_data['definition']}
카테고리: {term_data['category']}
예시: {term_data['examples']}
관련 테이블: {', '.join(term_data['related_tables'])}
            """.strip()
            
            doc = Document(
                page_content=content,
                metadata={
                    "type": "business_term",
                    "term": term_data["term"],
                    "category": term_data["category"],
                    "source": f"term_{term_data['term']}"
                }
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} business term documents")
        return documents
    
    async def _create_sql_example_documents(self) -> List[Document]:
        """SQL 예시 문서 생성"""
        sql_examples = [
            {
                "question": "모든 고객 목록을 보여주세요",
                "sql": "SELECT id, name, email, phone, created_at FROM customers ORDER BY created_at DESC;",
                "explanation": "customers 테이블의 모든 레코드를 최신 순으로 조회합니다.",
                "complexity": "simple",
                "keywords": ["고객", "목록", "전체", "모든"]
            },
            {
                "question": "총 주문 금액이 가장 높은 고객을 찾아주세요",
                "sql": """SELECT c.id, c.name, SUM(o.total_amount) as total_spent 
                         FROM customers c 
                         JOIN orders o ON c.id = o.customer_id 
                         GROUP BY c.id, c.name 
                         ORDER BY total_spent DESC 
                         LIMIT 1;""",
                "explanation": "고객별 총 주문 금액을 계산하여 가장 많이 구매한 고객을 조회합니다.",
                "complexity": "medium",
                "keywords": ["총", "주문", "금액", "높은", "고객", "최고"]
            },
            {
                "question": "카테고리별 제품 수량을 보여주세요",
                "sql": "SELECT category, COUNT(*) as product_count FROM products GROUP BY category ORDER BY product_count DESC;",
                "explanation": "제품을 카테고리별로 그룹화하여 각 카테고리의 제품 수를 조회합니다.",
                "complexity": "simple",
                "keywords": ["카테고리", "제품", "수량", "개수"]
            },
            {
                "question": "재고가 부족한 제품을 찾아주세요",
                "sql": "SELECT id, name, stock_quantity, category FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC;",
                "explanation": "재고가 10개 미만인 제품들을 재고 수량 순으로 조회합니다.",
                "complexity": "simple",
                "keywords": ["재고", "부족", "제품", "적은"]
            },
            {
                "question": "최근 한 달간 주문 현황을 보여주세요",
                "sql": """SELECT DATE(order_date) as order_day, 
                         COUNT(*) as order_count,
                         SUM(total_amount) as daily_revenue
                         FROM orders 
                         WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
                         GROUP BY DATE(order_date)
                         ORDER BY order_day DESC;""",
                "explanation": "최근 30일간의 일별 주문 건수와 매출을 조회합니다.",
                "complexity": "medium",
                "keywords": ["최근", "한 달", "주문", "현황", "매출"]
            }
        ]
        
        documents = []
        for i, example in enumerate(sql_examples):
            content = f"""
질문: {example['question']}
SQL 쿼리:
{example['sql']}

설명: {example['explanation']}
복잡도: {example['complexity']}
키워드: {', '.join(example['keywords'])}
            """.strip()
            
            doc = Document(
                page_content=content,
                metadata={
                    "type": "sql_example",
                    "complexity": example["complexity"],
                    "keywords": example["keywords"],
                    "source": f"sql_example_{i}"
                }
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} SQL example documents")
        return documents
    
    def create_qa_chain(self) -> ConversationalRetrievalChain:
        """질의응답 체인 생성"""
        template = """
당신은 데이터베이스 전문가입니다. 주어진 컨텍스트와 대화 기록을 바탕으로 사용자의 질문에 답변하세요.

컨텍스트:
{context}

대화 기록:
{chat_history}

사용자 질문: {question}

답변할 때 다음 사항을 고려하세요:
1. 테이블 스키마 정보를 정확히 활용하세요
2. 비즈니스 용어를 올바르게 해석하세요
3. 적절한 SQL 쿼리를 제안하세요
4. 안전한 SELECT 문만 사용하세요
5. 명확하고 구체적으로 답변하세요

답변:"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
        
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            ),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": prompt},
            return_source_documents=True,
            verbose=True
        )
    
    async def ask_question(self, question: str) -> Dict[str, Any]:
        """질문 처리"""
        try:
            qa_chain = self.create_qa_chain()
            
            result = qa_chain({
                "question": question
            })
            
            return {
                "answer": result["answer"],
                "source_documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in result.get("source_documents", [])
                ],
                "chat_history": [
                    {"type": "human" if i % 2 == 0 else "ai", "content": str(msg)}
                    for i, msg in enumerate(self.memory.chat_memory.messages)
                ]
            }
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "answer": f"질문 처리 중 오류가 발생했습니다: {str(e)}",
                "source_documents": [],
                "chat_history": []
            }
    
    async def get_relevant_context(self, question: str, k: int = 5) -> List[Dict[str, Any]]:
        """관련 컨텍스트 검색"""
        try:
            docs = self.vectorstore.similarity_search(question, k=k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)
                }
                for doc in docs
            ]
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []
    
    def clear_memory(self):
        """대화 메모리 초기화"""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """벡터 스토어 통계"""
        try:
            collection = self.vectorstore._collection
            return {
                "total_documents": collection.count(),
                "collection_name": collection.name,
                "embedding_dimension": len(self.embeddings.embed_query("test"))
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"error": str(e)}


# 전역 LangChain RAG 엔진 인스턴스
langchain_rag_engine = LangChainRAGEngine()