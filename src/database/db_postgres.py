"""PostgreSQL 전용 DB 유틸 (step6 전용)

중요:
- 기존 SQLite 연결(`src/database/db.py`)은 유지합니다.
- 이 파일은 step6에서만 PostgreSQL을 쓰기 위한 "별도" 연결 모듈입니다.

환경변수 (기본값 포함):
- POSTGRES_USER (default: postgres)
- POSTGRES_PASSWORD (default: postgres)
- POSTGRES_DB (default: nestjs_db)  # 요청사항: DB명 동일
- POSTGRES_HOST (default: localhost)
- POSTGRES_PORT (default: 5432)

또는 한 줄 URL로 지정:
- STEP6_POSTGRES_DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/db"
"""

import os
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def get_postgres_database_url() -> str:
    url = os.getenv("STEP6_POSTGRES_DATABASE_URL")
    if url and url.strip():
        return url.strip()

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "nestjs_db")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    user_enc = quote_plus(user)
    password_enc = quote_plus(password)
    host_enc = host.strip()
    port_enc = str(port).strip()
    dbname_enc = dbname.strip()

    return f"postgresql+psycopg2://{user_enc}:{password_enc}@{host_enc}:{port_enc}/{dbname_enc}"


def get_engine_postgres(database_url: Optional[str] = None):
    url = database_url or get_postgres_database_url()
    return create_engine(url, echo=False, pool_pre_ping=True)


def init_database_postgres(database_url: Optional[str] = None):
    """PostgreSQL에 테이블 생성"""
    engine = get_engine_postgres(database_url=database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session_postgres(engine=None, database_url: Optional[str] = None):
    """PostgreSQL 세션 반환"""
    if engine is None:
        engine = get_engine_postgres(database_url=database_url)
    Session = sessionmaker(bind=engine)
    return Session()


