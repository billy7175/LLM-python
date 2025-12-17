"""Step 2: Context Assembler를 사용한 인터랙티브 챗

step1_chat_with_memory.py와의 차이:
- step1: conversation_history를 그대로 LLM에 전송 (토큰 제한 없음)
- step2: Context Assembler가 토큰 제한 내에서 메모리를 선택하여 조립

Context Assembler의 장점:
1. 시스템 프롬프트 자동 추가
2. 토큰 제한 관리 (max_tokens 내에서만 메모리 선택)
3. 메시지 순서 강제 (system → memories → user)
"""

from src.llm.ollama_provider import OllamaProvider
from src.prompt.context_assembler import ContextAssembler


def main():
    """인터랙티브 챗 루프 (Context Assembler 사용)"""
    print("=" * 60)
    print("로컬 LLM 챗 (Context Assembler 사용 - 토큰 제한 관리)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)
    
    # Provider 생성
    provider = OllamaProvider(model="llama3")
    
    # Context Assembler 생성 (토큰 제한 설정)
    context_assembler = ContextAssembler(max_tokens=4096)
    
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
            print("\n[LLM]: ", end="", flush=True)
            
            # Context Assembler로 메시지 조립 (토큰 제한 관리)
            messages = context_assembler.build_context(
                memories=conversation_history,
                user_message=user_input
            )
            
            # LLM 호출
            response = provider.generate(messages, temperature=0.7)
            
            # 사용자 메시지와 LLM 응답을 대화 기록에 추가
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # 응답 출력
            print(response)
            
            # 디버그 정보 (선택사항)
            selected_count = len(messages) - 2  # system과 user 제외
            print(f"\n[디버그] 전체 메모리: {len(conversation_history)}개, 선택된 메모리: {selected_count}개")
            
        except KeyboardInterrupt:
            print("\n\n👋 안녕히가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print("💡 Ollama 서버가 실행 중인지 확인하세요: ollama serve")


if __name__ == "__main__":
    main()

