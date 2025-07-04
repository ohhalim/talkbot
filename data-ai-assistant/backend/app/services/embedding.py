import openai
from typing import List, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """임베딩 서비스 클래스"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-ada-002"
    
    async def embed_text(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트를 벡터로 변환"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise
    
    async def embed_document_for_search(self, content: str, metadata: Dict[str, Any]) -> str:
        """검색을 위한 문서 임베딩 준비"""
        # 메타데이터와 함께 검색에 최적화된 텍스트 생성
        search_text = f"{content}\n\n"
        
        # 메타데이터 추가
        if metadata.get('title'):
            search_text = f"Title: {metadata['title']}\n{search_text}"
        if metadata.get('description'):
            search_text = f"{search_text}Description: {metadata['description']}\n"
        if metadata.get('tags'):
            search_text = f"{search_text}Tags: {', '.join(metadata['tags'])}\n"
        
        return search_text.strip()


# 전역 임베딩 서비스 인스턴스
embedding_service = EmbeddingService()