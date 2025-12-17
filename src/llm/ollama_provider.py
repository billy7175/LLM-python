"""Ollama Provider 구현"""

import requests
from typing import List, Dict, Optional
from .llm_provider import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama HTTP API를 사용한 LLM 프로바이더"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: int = 120
    ):
        """
        Args:
            base_url: Ollama 서버 URL
            model: 사용할 모델 이름
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.chat_endpoint = f"{self.base_url}/api/chat"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Ollama API를 통해 LLM 응답 생성
        
        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}, ...]
            temperature: 생성 온도 (기본값: None, Ollama 기본값 사용)
            max_tokens: 최대 토큰 수 (기본값: None, Ollama 기본값 사용)
            **kwargs: 추가 Ollama 옵션
            
        Returns:
            생성된 응답 텍스트
        """
        # Ollama API 요청 페이로드 구성
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,  # 스트리밍은 나중에 구현
        }
        
        # 옵션이 제공된 경우만 추가
        if temperature is not None:
            payload["options"] = payload.get("options", {})
            payload["options"]["temperature"] = temperature
        
        if max_tokens is not None:
            payload["options"] = payload.get("options", {})
            payload["options"]["num_predict"] = max_tokens
        
        # kwargs의 options도 병합
        if "options" in kwargs:
            payload["options"] = {**payload.get("options", {}), **kwargs["options"]}
        
        try:
            response = requests.post(
                self.chat_endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Ollama API 응답에서 메시지 추출
            if "message" in result and "content" in result["message"]:
                return result["message"]["content"]
            else:
                raise ValueError(f"Unexpected response format: {result}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API request failed: {e}") from e

