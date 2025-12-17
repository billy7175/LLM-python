"""Step 3: Chat Manager를 사용한 인터랙티브 챗

step2_context_assembler_interactive.py와의 차이:

[step2 방식]
- Context Assembler와 LLM Provider를 직접 사용
- 메모리(conversation_history)를 직접 관리
- 모든 로직이 main() 함수에 직접 들어있음

[step3 방식 - 이렇게 다르게 동작]
- ChatManager 클래스를 사용
- chat(user_message) 하나로 모든 처리
- 내부에서 Context Assembler, LLM Provider, 메모리 관리 모두 처리
- 재사용 가능한 구조

예시:
  step2: messages = context_assembler.build_context(...)
         response = provider.generate(messages)
         conversation_history.append(...)
  
  step3: response = chat_manager.chat(user_message)  # 끝!
"""

from src.chat.chat_manager import ChatManager


def main():
    """인터랙티브 챗 루프 (Chat Manager 사용)"""
    print("=" * 60)
    print("로컬 LLM 챗 (Chat Manager 사용)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)
    
    # ===== step2와의 차이점 1: 클래스 사용 =====
    # step2: provider = OllamaProvider()
    #        context_assembler = ContextAssembler()
    #        conversation_history = []
    # step3: 모든 것이 ChatManager 클래스 내부에서 관리됨
    chat_manager = ChatManager()
    
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
            
            # ===== step2와의 차이점 2: 한 줄로 처리 =====
            # step2: messages = context_assembler.build_context(conversation_history, user_input)
            #        response = provider.generate(messages, temperature=0.7)
            #        conversation_history.append({"role": "user", "content": user_input})
            #        conversation_history.append({"role": "assistant", "content": response})
            # step3: chat() 메서드가 모든 것을 내부에서 처리 (한 줄로 끝!)
            response = chat_manager.chat(user_input)
            
            # 응답 출력
            print(response)
            
            # ===== step2와의 차이점 3: 메서드로 접근 =====
            # step2: len(conversation_history)  # 직접 접근
            # step3: 메서드로 접근 (캡슐화)
            history = chat_manager.get_conversation_history()
            print(f"\n[디버그] 전체 대화 기록: {len(history)}개")
            
        except KeyboardInterrupt:
            print("\n\n👋 안녕히가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print("💡 Ollama 서버가 실행 중인지 확인하세요: ollama serve")


if __name__ == "__main__":
    main()

