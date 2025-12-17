"""LLM Provider 추상화 계층"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMProvider(ABC):
    """LLM 프로바이더 인터페이스"""
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        LLM을 사용하여 응답 생성
        
        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}, ...]
            temperature: 생성 온도 (0.0 ~ 1.0)
            max_tokens: 최대 토큰 수
            **kwargs: 추가 옵션
            
        Returns:
            생성된 응답 텍스트
        """
        pass

