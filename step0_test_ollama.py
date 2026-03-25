"""Ollama Provider 테스트 스크립트"""

import sys
import time
from src.llm.ollama_provider import OllamaProvider


def test_ollama():
    """Ollama Provider 기본 테스트"""
    print("Testing Ollama Provider...")
    print("-" * 50)
    
    # Provider 생성
    provider = OllamaProvider(model="llama3")
    
    # 테스트 메시지
    messages = [
        {"role": "user", "content": "안녕하세요! 간단히 자기소개 부탁드립니다."}
    ]
    
    try:
        print("Sending request to Ollama...")
        start_time = time.perf_counter()
        response = provider.generate(messages, temperature=0.7)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print("\n✅ Success!")
        print(f"⏱️ Elapsed: {elapsed_ms:.0f} ms")
        print("\nResponse:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure Ollama is running:")
        print("   ollama serve")
        print("   ollama pull llama3")
        sys.exit(1)


if __name__ == "__main__":
    test_ollama()

