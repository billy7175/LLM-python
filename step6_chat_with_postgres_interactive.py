"""
Step 6: PostgreSQL 저장/로드로 동작하는 인터랙티브 챗

중요:
- 기존 step5(`step5_chat_with_db_interactive.py`)는 SQLite를 사용합니다.
- 이 step6 스크립트는 **PostgreSQL만** 사용합니다.
- 기존 SQLite 구현/파일은 건드리지 않습니다.
"""

from dotenv import load_dotenv

from src.chat.chat_manager_with_db import ChatManagerWithDB
from src.database.db_postgres import get_session_postgres
from src.memory.memory_manager import MemoryManager


def main():
    load_dotenv()

    print("=" * 60)
    print("로컬 LLM 챗 (PostgreSQL 저장/로드)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)

    # 기본 세션 ID (프로그램 재시작 시에도 같은 대화 계속)
    session_id = "default"

    # Postgres 세션/MemoryManager를 만들어 ChatManagerWithDB에 주입
    pg_session = get_session_postgres()
    memory_manager = MemoryManager(session=pg_session)
    chat_manager = ChatManagerWithDB(
        conversation_id=session_id,
        memory_manager=memory_manager,
    )

    while True:
        user_input = input("\n[당신]: ").strip()

        if user_input.lower() in ["quit", "exit", "종료", "q"]:
            print("\n👋 안녕히가세요!")
            print(f"💾 대화 기록이 PostgreSQL에 저장되었습니다. (세션 ID: {session_id})")
            break

        if not user_input:
            continue

        try:
            response = chat_manager.chat(user_input)
            print(f"\n[봇]: {response}")
            print(f"(저장된 메시지 수: {chat_manager.get_message_count()})")
        except Exception as e:
            print(f"\n❌ 오류: {e}")
            print("💡 Postgres 컨테이너 실행/접속정보/드라이버 설치(psycopg2-binary)를 확인하세요.")


if __name__ == "__main__":
    main()


