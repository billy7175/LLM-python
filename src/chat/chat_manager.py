"""Chat Manager - 대화 관리 클래스

Context Assembler와 LLM Service를 통합하여 챗 기능을 제공합니다.
"""

from typing import List, Dict, Optional
from src.llm.ollama_provider import OllamaProvider
from src.llm.llm_provider import LLMProvider
from src.prompt.context_assembler import ContextAssembler


class ChatManager:
    """대화를 관리하는 매니저 클래스"""
    
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        context_assembler: Optional[ContextAssembler] = None,
        max_tokens: int = 4096
    ):
        """
        Args:
            llm_provider: LLM 프로바이더 (기본값: OllamaProvider)
            context_assembler: Context Assembler (기본값: 새로 생성)
            max_tokens: 최대 토큰 수
        """
        self.llm_provider = llm_provider or OllamaProvider()
        self.context_assembler = context_assembler or ContextAssembler(max_tokens=max_tokens)
        
        # 대화 기록 (메모리 - DB 없음 단계)
        self.conversation_history: List[Dict[str, str]] = []
    
    def chat(
        self,
        user_message: str,
        temperature: float = 0.7,
        search_results: Optional[str] = None
    ) -> str:
        """
        사용자 메시지를 받아 LLM 응답을 반환
        
        Args:
            user_message: 사용자 메시지
            temperature: 생성 온도
            search_results: 검색 결과 (선택사항)
            
        Returns:
            LLM 응답
        """
        # Context Assembler로 메시지 조립
        messages = self.context_assembler.build_context(
            memories=self.conversation_history,
            user_message=user_message,
            search_results=search_results
        )
        
        # LLM 호출
        response = self.llm_provider.generate(
            messages,
            temperature=temperature
        )
        
        # 대화 기록에 추가 (메모리 저장)
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """현재 대화 기록 반환"""
        return self.conversation_history.copy()
    
    def clear_history(self):
        """대화 기록 초기화"""
        self.conversation_history = []

