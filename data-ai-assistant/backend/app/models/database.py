from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    queries = relationship("Query", back_populates="user")


class Query(Base):
    """질의 모델"""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    execution_time = Column(Float, nullable=True)  # 실행 시간 (초)
    status = Column(String(20), default="pending")  # pending, success, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    user = relationship("User", back_populates="queries")
    feedbacks = relationship("Feedback", back_populates="query")


class Feedback(Base):
    """피드백 모델"""
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 점수
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    query = relationship("Query", back_populates="feedbacks")
    user = relationship("User")


class TableSchema(Base):
    """테이블 스키마 메타데이터"""
    __tablename__ = "table_schemas"
    
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    schema_name = Column(String(50), default="public")
    column_info = Column(Text, nullable=False)  # JSON 형태의 컬럼 정보
    description = Column(Text, nullable=True)
    sample_data = Column(Text, nullable=True)  # 샘플 데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BusinessTerm(Base):
    """비즈니스 용어 사전"""
    __tablename__ = "business_terms"
    
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    examples = Column(Text, nullable=True)
    synonyms = Column(Text, nullable=True)  # 동의어
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SQLExample(Base):
    """SQL 예시"""
    __tablename__ = "sql_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    complexity = Column(String(20), default="simple")  # simple, medium, complex
    tags = Column(Text, nullable=True)  # 태그 (JSON 배열)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())