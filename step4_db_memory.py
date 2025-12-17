"""DB & Memory Manager 테스트"""

from src.database.db import init_database
from src.memory.memory_manager import MemoryManager
from src.database.models import Conversation, Message


def test_memory_manager():
    """Memory Manager 기본 동작 테스트"""
    print("=" * 60)
    print("DB & Memory Manager 테스트")
    print("=" * 60)
    
    # DB 초기화
    engine = init_database()
    print("\n✅ DB 초기화 완료")
    
    # Memory Manager 생성
    memory_manager = MemoryManager()
    print("✅ Memory Manager 생성 완료\n")
    
    # 1. 대화 세션 생성
    session_id = "test_session_001"
    conversation = memory_manager.get_or_create_conversation(session_id)
    print(f"✅ 대화 세션 생성: ID={conversation.id}, session_id={conversation.session_id}")
    
    # 2. 메시지 저장
    memory_manager.save_message(
        conversation_id=conversation.id,
        role="user",
        content="안녕하세요!"
    )
    memory_manager.save_message(
        conversation_id=conversation.id,
        role="assistant",
        content="안녕하세요! 무엇을 도와드릴까요?"
    )
    memory_manager.save_message(
        conversation_id=conversation.id,
        role="user",
        content="내 이름은 철수입니다"
    )
    memory_manager.save_message(
        conversation_id=conversation.id,
        role="assistant",
        content="반갑습니다 철수님!"
    )
    print("✅ 메시지 4개 저장 완료")
    
    # 3. 메시지 로드
    messages = memory_manager.load_recent_messages(conversation.id)
    print(f"\n✅ 메시지 로드 완료: {len(messages)}개")
    print("\n로드된 메시지:")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. [{msg['role']}]: {msg['content'][:50]}")
    
    # 4. 메시지 수 확인
    count = memory_manager.get_conversation_messages_count(conversation.id)
    print(f"\n✅ 대화 메시지 수: {count}개")
    
    # 5. 제한된 메시지 로드
    limited_messages = memory_manager.load_recent_messages(conversation.id, limit=2)
    print(f"\n✅ 최근 2개 메시지 로드: {len(limited_messages)}개")
    for i, msg in enumerate(limited_messages, 1):
        print(f"  {i}. [{msg['role']}]: {msg['content'][:50]}")
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_manager()

