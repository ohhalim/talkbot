import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """벡터 데이터베이스 관리 클래스"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMADB_PERSIST_DIRECTORY,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self._initialize_collections()
    
    def _initialize_collections(self):
        """컬렉션 초기화"""
        self.collections = {
            "table_schemas": self._get_or_create_collection(
                "table_schemas",
                metadata={"description": "Database table schemas and metadata"}
            ),
            "business_terms": self._get_or_create_collection(
                "business_terms",
                metadata={"description": "Business terminology and definitions"}
            ),
            "sql_examples": self._get_or_create_collection(
                "sql_examples",
                metadata={"description": "SQL query examples and patterns"}
            )
        }
    
    def _get_or_create_collection(self, name: str, metadata: Dict[str, Any] = None):
        """컬렉션 생성 또는 조회"""
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """문서 추가"""
        try:
            collection = self.collections[collection_name]
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to {collection_name}")
        except Exception as e:
            logger.error(f"Error adding documents to {collection_name}: {str(e)}")
            raise
    
    async def search_similar(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """유사 문서 검색"""
        try:
            collection = self.collections[collection_name]
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            
            # 결과 포맷팅
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                    'id': results['ids'][0][i]
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching in {collection_name}: {str(e)}")
            raise
    
    async def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: str,
        metadata: Dict[str, Any]
    ):
        """문서 업데이트"""
        try:
            collection = self.collections[collection_name]
            collection.update(
                ids=[document_id],
                documents=[document],
                metadatas=[metadata]
            )
            logger.info(f"Updated document {document_id} in {collection_name}")
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {str(e)}")
            raise
    
    async def delete_document(self, collection_name: str, document_id: str):
        """문서 삭제"""
        try:
            collection = self.collections[collection_name]
            collection.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 통계 조회"""
        try:
            collection = self.collections[collection_name]
            count = collection.count()
            return {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error(f"Error getting stats for {collection_name}: {str(e)}")
            raise


# 전역 벡터 스토어 인스턴스
vector_store = VectorStore()