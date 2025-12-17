"""Chat Manager with DB - DB를 사용하는 Chat Manager

기존 ChatManager와의 차이:
- 기존: 메모리(리스트)만 사용
- 이 버전: Memory Manager를 사용하여 DB에 저장
"""

from typing import List, Dict, Optional
from src.llm.ollama_provider import OllamaProvider
from src.llm.llm_provider import LLMProvider
from src.prompt.context_assembler import ContextAssembler
from src.memory.memory_manager import MemoryManager


class ChatManagerWithDB:
    """DB를 사용하는 대화 관리 클래스"""
    
    def __init__(
        self,
        conversation_id: str,
        llm_provider: Optional[LLMProvider] = None,
        context_assembler: Optional[ContextAssembler] = None,
        memory_manager: Optional[MemoryManager] = None,
        max_tokens: int = 4096
    ):
        """
        Args:
            conversation_id: 대화 세션 ID
            llm_provider: LLM 프로바이더 (기본값: OllamaProvider)
            context_assembler: Context Assembler (기본값: 새로 생성)
            memory_manager: Memory Manager (기본값: 새로 생성)
            max_tokens: 최대 토큰 수
        """
        self.conversation_id = conversation_id
        self.llm_provider = llm_provider or OllamaProvider()
        self.context_assembler = context_assembler or ContextAssembler(max_tokens=max_tokens)
        self.memory_manager = memory_manager or MemoryManager()
        
        # 대화 세션 가져오기 또는 생성
        self.conversation = self.memory_manager.get_or_create_conversation(conversation_id)
    
    def chat(
        self,
        user_message: str,
        temperature: float = 0.7,
        search_results: Optional[str] = None
    ) -> str:
        """
        사용자 메시지를 받아 LLM 응답을 반환 (DB 저장/로드)
        
        Args:
            user_message: 사용자 메시지
            temperature: 생성 온도
            search_results: 검색 결과 (선택사항)
            
        Returns:
            LLM 응답
        """
        # 1. DB에서 최근 메시지 로드
        memories = self.memory_manager.load_recent_messages(self.conversation.id)
        
        # 2. Context Assembler로 메시지 조립
        messages = self.context_assembler.build_context(
            memories=memories,
            user_message=user_message,
            search_results=search_results
        )
        
        # 3. LLM 호출
        response = self.llm_provider.generate(
            messages,
            temperature=temperature
        )
        
        # 4. DB에 저장
        self.memory_manager.save_message(
            conversation_id=self.conversation.id,
            role="user",
            content=user_message
        )
        self.memory_manager.save_message(
            conversation_id=self.conversation.id,
            role="assistant",
            content=response
        )
        
        return response
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """DB에서 대화 기록 반환"""
        return self.memory_manager.load_recent_messages(self.conversation.id)
    
    def get_message_count(self) -> int:
        """대화의 메시지 수 반환"""
        return self.memory_manager.get_conversation_messages_count(self.conversation.id)

