"""Step 5: Chat Manager with DB - DB 저장/로드가 가능한 인터랙티브 챗

step3와 step4의 결합:

[step3 방식]
- ChatManager 클래스 사용
- 메모리(리스트)만 사용
- 프로그램 종료 시 대화 기록 사라짐
- conversation_history = [] (메모리)

[step4에서 구현한 것]
- DB 스키마 생성
- Memory Manager 구현 (DB 저장/로드 기능)
- 하지만 Chat Manager와 연결 안 됨

[step5 방식 - 이렇게 다르게 동작]
- ChatManagerWithDB 클래스 사용
- Memory Manager를 통합하여 DB에 저장
- 프로그램 종료 후에도 대화 기록 유지
- DB에서 메시지를 로드하여 기억

예시:
  step3: self.conversation_history.append(...)  # 메모리에만 저장
  
  step5: memory_manager.save_message(...)  # DB에 저장
         memories = memory_manager.load_recent_messages(...)  # DB에서 로드
"""

# import uuid  # 향후 새 세션 생성 시 사용
from src.chat.chat_manager_with_db import ChatManagerWithDB


def main():
    """인터랙티브 챗 루프 (DB 사용)"""
    print("=" * 60)
    print("로컬 LLM 챗 (DB 저장/로드)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)
    
    # ===== 1단계: 기본 세션 사용 =====
    # 방법 1: 항상 같은 세션 ID 사용 (프로그램 재시작 시에도 같은 대화 계속)
    session_id = "default"
    
    # 향후 확장 (주석 처리):
    # 방법 2: 매번 새 세션 생성
    # session_id = str(uuid.uuid4())
    
    # 방법 3: 사용자 입력 받기
    # session_id = input("세션 ID를 입력하세요 (엔터: default): ").strip() or "default"
    
    print(f"\n세션 ID: {session_id}")
    print("(이 세션 ID로 대화 기록이 DB에 저장됩니다)")
    print("(프로그램을 재시작해도 같은 대화를 이어서 진행할 수 있습니다)\n")
    
    # ===== step3와의 차이점: DB를 사용하는 Chat Manager =====
    # step3: chat_manager = ChatManager()  # 메모리만 사용
    # step4: Memory Manager 구현됨 (하지만 Chat Manager와 연결 안 됨)
    # step5: DB를 사용하는 ChatManagerWithDB 사용 (step4의 Memory Manager 통합)
    chat_manager = ChatManagerWithDB(conversation_id=session_id)
    
    while True:
        # 사용자 입력
        user_input = input("\n[당신]: ").strip()
        
        # 종료 명령
        if user_input.lower() in ['quit', 'exit', '종료', 'q']:
            print("\n👋 안녕히가세요!")
            print(f"💾 대화 기록이 DB에 저장되었습니다. (세션 ID: {session_id})")
            print("   프로그램을 다시 실행하면 같은 대화를 이어서 진행할 수 있습니다.")
            break
        
        if not user_input:
            continue
        
        try:
            print("\n[LLM]: ", end="", flush=True)
            
            # ===== step3와의 차이점: 내부에서 DB 저장/로드 =====
            # step3: 메모리에만 저장 (self.conversation_history.append)
            # step4: Memory Manager로 DB 저장/로드 가능 (하지만 Chat Manager에서 사용 안 함)
            # step5: DB에 저장되고, DB에서 로드됨 (step4의 Memory Manager 사용)
            response = chat_manager.chat(user_input)
            
            # 응답 출력
            print(response)
            
            # 디버그 정보
            message_count = chat_manager.get_message_count()
            print(f"\n[디버그] DB에 저장된 메시지 수: {message_count}개")
            
        except KeyboardInterrupt:
            print("\n\n👋 안녕히가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print("💡 Ollama 서버가 실행 중인지 확인하세요: ollama serve")


if __name__ == "__main__":
    main()

