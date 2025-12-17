"""Context Assembler - LLM에 보낼 메시지 조립"""

from typing import List, Dict, Optional
import os


class ContextAssembler:
    """LLM에 보낼 메시지 컨텍스트를 조립하는 클래스"""
    
    def __init__(
        self,
        system_prompt_template: str = None,
        max_tokens: int = 4096,
        chars_per_token: float = 4.0  # 대략 1 토큰 ≈ 4 문자
    ):
        """
        Args:
            system_prompt_template: 시스템 프롬프트 템플릿 경로 또는 텍스트
            max_tokens: 최대 토큰 수
            chars_per_token: 토큰당 문자 수 추정값
        """
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        
        # 시스템 프롬프트 로드
        if system_prompt_template is None:
            # 기본 템플릿 경로
            template_path = os.path.join(
                os.path.dirname(__file__),
                "templates",
                "base_system.txt"
            )
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    self.system_prompt = f.read().strip()
            else:
                self.system_prompt = "You are a helpful assistant."
        elif os.path.isfile(system_prompt_template):
            # 파일 경로인 경우
            with open(system_prompt_template, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
        else:
            # 직접 텍스트인 경우
            self.system_prompt = system_prompt_template
    
    def _estimate_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수를 추정
        
        Args:
            text: 추정할 텍스트
            
        Returns:
            추정된 토큰 수
        """
        return int(len(text) / self.chars_per_token)
    
    def _estimate_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        메시지 리스트의 전체 토큰 수 추정
        
        Args:
            messages: 메시지 리스트
            
        Returns:
            추정된 토큰 수
        """
        total_chars = 0
        for msg in messages:
            # role + content + 메타데이터 추정
            content = msg.get("content", "")
            role = msg.get("role", "")
            total_chars += len(content) + len(role) + 10  # 메타데이터 추정
        
        return int(total_chars / self.chars_per_token)
    
    def build_context(
        self,
        memories: List[Dict[str, str]],
        user_message: str,
        search_results: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        LLM에 보낼 메시지 컨텍스트 조립
        
        Args:
            memories: 이전 대화 기록 (user/assistant 메시지)
            user_message: 현재 사용자 메시지
            search_results: 검색 결과 (선택사항)
            
        Returns:
            LLM에 보낼 메시지 리스트
        """
        # 1. 시스템 프롬프트로 시작
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 2. 검색 결과가 있으면 시스템 메시지에 추가
        if search_results:
            messages[0]["content"] += f"\n\nSearch Results:\n{search_results}"
        
        # 3. 이전 대화 기록 추가 (토큰 제한 내에서)
        selected_memories = self._select_memories_within_limit(memories)
        messages.extend(selected_memories)
        
        # 4. 현재 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def _select_memories_within_limit(
        self,
        memories: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        토큰 제한 내에서 메모리 선택 (최근 메시지 우선)
        
        Args:
            memories: 전체 메모리 리스트
            
        Returns:
            선택된 메모리 리스트
        """
        if not memories:
            return []
        
        # 시스템 프롬프트 토큰 추정
        system_tokens = self._estimate_tokens(self.system_prompt)
        # 사용자 메시지를 위한 여유 공간 (대략 추정)
        reserved_tokens = system_tokens + 100
        available_tokens = self.max_tokens - reserved_tokens
        
        # 최근 메시지부터 역순으로 선택
        selected = []
        current_tokens = 0
        
        # 역순으로 순회 (최신 메시지부터)
        for memory in reversed(memories):
            memory_tokens = self._estimate_tokens(
                memory.get("content", "") + memory.get("role", "")
            )
            
            if current_tokens + memory_tokens <= available_tokens:
                selected.insert(0, memory)  # 앞에 추가 (순서 유지)
                current_tokens += memory_tokens
            else:
                # 토큰 초과 시 중단
                break
        
        return selected


def build_context(
    memories: List[Dict[str, str]],
    user_message: str,
    search_results: Optional[str] = None,
    max_tokens: int = 4096
) -> List[Dict[str, str]]:
    """
    편의 함수: Context Assembler를 사용하여 컨텍스트 생성
    
    Args:
        memories: 이전 대화 기록
        user_message: 현재 사용자 메시지
        search_results: 검색 결과 (선택사항)
        max_tokens: 최대 토큰 수
        
    Returns:
        LLM에 보낼 메시지 리스트
    """
    assembler = ContextAssembler(max_tokens=max_tokens)
    return assembler.build_context(memories, user_message, search_results)

