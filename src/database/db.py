"""Database 초기화 및 설정"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, init_db as create_tables

# 데이터베이스 경로 (SQLite)
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "chat.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"


def get_engine():
    """데이터베이스 엔진 반환"""
    # 디렉토리 생성
    os.makedirs(DB_DIR, exist_ok=True)
    
    engine = create_engine(DATABASE_URL, echo=False)
    return engine


def init_database():
    """데이터베이스 초기화 (테이블 생성)"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    """데이터베이스 세션 반환"""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

