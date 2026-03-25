"""Step 1+: 간단한 기억 기능이 있는 챗 (메모리 기반 - DB 없음)

1단계 확장 버전: conversation_history 리스트로 메모리 관리
- Python 리스트로 대화 기록 저장
- 프로그램 종료 시 사라짐 (메모리 저장)
- 토큰 제한 관리 없음 (대화가 길어지면 느려질 수 있음)
"""

from src.llm.ollama_provider import OllamaProvider
import time


def main():
    """인터랙티브 챗 루프 (기억 있음)"""
    print("=" * 60)
    print("로컬 LLM 챗 (기억 있음 - 이전 대화 포함)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)
    
    # Provider 생성
    provider = OllamaProvider(model="llama3")
    
    # 대화 기록 저장 (메모리 - 프로그램 종료 시 사라짐)
    conversation_history = []
    
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
            # 사용자 메시지를 대화 기록에 추가
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            print("\n[LLM]: ", end="", flush=True)
            
            # 이전 대화 기록을 모두 포함하여 LLM 호출
            start_time = time.perf_counter()
            response = provider.generate(conversation_history, temperature=0.7)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # LLM 응답을 대화 기록에 추가
            conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
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

