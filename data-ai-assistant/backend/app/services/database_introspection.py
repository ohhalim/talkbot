import json
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)


class DatabaseIntrospection:
    """데이터베이스 메타데이터 수집 클래스"""
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.inspector = inspect(self.engine)
    
    def get_all_tables(self) -> List[str]:
        """모든 테이블 이름 조회"""
        return self.inspector.get_table_names()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """테이블 스키마 정보 조회"""
        try:
            columns = self.inspector.get_columns(table_name)
            primary_keys = self.inspector.get_pk_constraint(table_name)
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            indexes = self.inspector.get_indexes(table_name)
            
            schema_info = {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": col.get("default"),
                        "primary_key": col["name"] in primary_keys.get("constrained_columns", [])
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "column": fk["constrained_columns"][0],
                        "referenced_table": fk["referred_table"],
                        "referenced_column": fk["referred_columns"][0]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx["unique"]
                    }
                    for idx in indexes
                ]
            }
            
            return schema_info
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {str(e)}")
            raise
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """테이블 샘플 데이터 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT * FROM {table_name} LIMIT {limit}")
                )
                columns = result.keys()
                rows = result.fetchall()
                
                return [
                    {col: str(row[i]) for i, col in enumerate(columns)}
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting sample data for table {table_name}: {str(e)}")
            return []
    
    def generate_table_description(self, table_name: str) -> str:
        """테이블 설명 생성"""
        try:
            schema = self.get_table_schema(table_name)
            sample_data = self.get_sample_data(table_name, 3)
            
            description = f"Table: {table_name}\n\n"
            description += "Columns:\n"
            
            for col in schema["columns"]:
                description += f"- {col['name']} ({col['type']})"
                if col["primary_key"]:
                    description += " [Primary Key]"
                if not col["nullable"]:
                    description += " [Not Null]"
                description += "\n"
            
            if schema["foreign_keys"]:
                description += "\nForeign Keys:\n"
                for fk in schema["foreign_keys"]:
                    description += f"- {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}\n"
            
            if sample_data:
                description += f"\nSample Data (first 3 rows):\n"
                for i, row in enumerate(sample_data, 1):
                    description += f"Row {i}: {row}\n"
            
            return description
        except Exception as e:
            logger.error(f"Error generating description for table {table_name}: {str(e)}")
            return f"Table: {table_name} (Error loading details)"
    
    def create_sample_tables(self):
        """샘플 테이블 생성 (MVP용)"""
        sample_tables = [
            """
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                category VARCHAR(50),
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        
        sample_data = [
            """
            INSERT INTO customers (name, email, phone) VALUES 
            ('김철수', 'kim@example.com', '010-1234-5678'),
            ('박영희', 'park@example.com', '010-2345-6789'),
            ('이민수', 'lee@example.com', '010-3456-7890')
            ON CONFLICT (email) DO NOTHING;
            """,
            """
            INSERT INTO products (name, price, category, stock_quantity) VALUES 
            ('노트북', 1500000, '전자제품', 10),
            ('마우스', 50000, '전자제품', 25),
            ('키보드', 120000, '전자제품', 15)
            ON CONFLICT DO NOTHING;
            """,
            """
            INSERT INTO orders (customer_id, product_id, quantity, total_amount) VALUES 
            (1, 1, 1, 1500000),
            (2, 2, 2, 100000),
            (3, 3, 1, 120000)
            ON CONFLICT DO NOTHING;
            """
        ]
        
        try:
            with self.engine.connect() as conn:
                # 테이블 생성
                for table_sql in sample_tables:
                    conn.execute(text(table_sql))
                
                # 샘플 데이터 삽입
                for data_sql in sample_data:
                    conn.execute(text(data_sql))
                
                conn.commit()
                logger.info("Sample tables and data created successfully")
        except Exception as e:
            logger.error(f"Error creating sample tables: {str(e)}")
            raise


# 전역 데이터베이스 인트로스펙션 인스턴스
db_introspection = DatabaseIntrospection()