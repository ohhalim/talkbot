#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
"""
import asyncio
import logging
from app.core.database import engine, Base
from app.models.database import *
from app.services.database_introspection import db_introspection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """테이블 생성"""
    try:
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")
        
        # 샘플 데이터 생성
        db_introspection.create_sample_tables()
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(create_tables())