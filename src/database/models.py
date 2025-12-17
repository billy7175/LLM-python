"""Database Models - SQLAlchemy 모델 정의"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Conversation(Base):
    """대화 세션 테이블"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id='{self.session_id}', title='{self.title}')>"


class Message(Base):
    """메시지 테이블"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    message_metadata = Column(JSON, nullable=True)  # 추가 정보 (토큰 수, 검색 사용 여부 등)
    
    # 관계
    conversation = relationship("Conversation", back_populates="messages")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint("role IN ('system', 'user', 'assistant', 'tool', 'search')", name='check_role'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"


def init_db(database_url: str = "sqlite:///data/chat.db"):
    """
    데이터베이스 초기화 (테이블 생성)
    
    Args:
        database_url: 데이터베이스 URL (기본값: SQLite)
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """
    데이터베이스 세션 생성
    
    Args:
        engine: SQLAlchemy 엔진
        
    Returns:
        세션 객체
    """
    Session = sessionmaker(bind=engine)
    return Session()

