"""Step 1: 간단한 인터랙티브 챗 (기억 없음 - 매번 독립적)

1단계 수준: LLM Provider만 구현된 상태
- 기억 기능 없음
- 매번 새로운 메시지만 전송
"""

from src.llm.ollama_provider import OllamaProvider
import time


def main():
    """인터랙티브 챗 루프"""
    print("=" * 60)
    print("로컬 LLM 챗 (기억 없음 - 매번 독립적)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)
    print("[봇]: 안녕하세요! 반가워요 😊 무엇을 도와드릴까요?")
    
    # Provider 생성
    provider = OllamaProvider(model="llama3")
    
    while True:
        # 사용자 입력
        user_input = input("\n[당신]: ").strip()
        
        # 종료 명령
        if user_input.lower() in ['quit', 'exit', '종료', 'q']:
            print("\n👋 안녕히가세요!")
            break
        
        if not user_input:
            continue
        
        try:
            # 메시지 구성 (매번 독립적 - 기억 없음)
            messages = [
                {"role": "user", "content": user_input}
            ]
            
            print("\n[봇]: ", end="", flush=True)
            
            # LLM 호출
            start_time = time.perf_counter()
            response = provider.generate(messages, temperature=0.7)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # 응답 출력
            print(response)
            print(f"[속도] {elapsed_ms:.0f} ms ({elapsed_ms / 1000:.2f}s)")
            
        except KeyboardInterrupt:
            print("\n\n👋 안녕히가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print("💡 Ollama 서버가 실행 중인지 확인하세요: ollama serve")


if __name__ == "__main__":
    main()

