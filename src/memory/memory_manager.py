"""Memory Manager - 대화 기록 관리

핵심 개념: "기억은 저장이 아니라 재주입이다"
- 모든 대화를 DB에 저장
- 필요할 때 최근 메시지만 로드
- Context Assembler에 전달하여 LLM에게 재주입
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database.models import Conversation, Message
from ..database.db import get_session


class MemoryManager:
    """대화 기록을 관리하는 매니저"""
    
    def __init__(self, session: Optional[Session] = None):
        """
        Args:
            session: 데이터베이스 세션 (기본값: 새로 생성)
        """
        self.session = session or get_session()
    
    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        message_metadata: Optional[Dict] = None
    ) -> Message:
        """
        메시지를 데이터베이스에 저장
        
        Args:
            conversation_id: 대화 세션 ID
            role: 역할 (user, assistant 등)
            content: 메시지 내용
            message_metadata: 추가 정보 (선택사항)
            
        Returns:
            저장된 Message 객체
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=message_metadata
        )
        self.session.add(message)
        self.session.commit()
        return message
    
    def load_recent_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        최근 메시지를 로드 (최신순)
        
        Args:
            conversation_id: 대화 세션 ID
            limit: 최대 메시지 수 (None이면 전체)
            
        Returns:
            메시지 리스트 [{"role": "...", "content": "..."}, ...]
        """
        query = self.session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.timestamp))
        
        if limit:
            query = query.limit(limit)
        
        messages = query.all()
        
        # 최신순이므로 역순으로 정렬 (오래된 것부터)
        messages.reverse()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    def create_conversation(self, session_id: str, title: Optional[str] = None) -> Conversation:
        """
        새 대화 세션 생성
        
        Args:
            session_id: 세션 ID
            title: 대화 제목 (선택사항)
            
        Returns:
            생성된 Conversation 객체
        """
        conversation = Conversation(session_id=session_id, title=title)
        self.session.add(conversation)
        self.session.commit()
        return conversation
    
    def get_or_create_conversation(self, session_id: str) -> Conversation:
        """
        대화 세션 가져오기 또는 생성
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Conversation 객체
        """
        conversation = self.session.query(Conversation).filter(
            Conversation.session_id == session_id
        ).first()
        
        if not conversation:
            conversation = self.create_conversation(session_id)
        
        return conversation
    
    def get_conversation_messages_count(self, conversation_id: int) -> int:
        """
        대화의 메시지 수 반환
        
        Args:
            conversation_id: 대화 세션 ID
            
        Returns:
            메시지 수
        """
        return self.session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()

