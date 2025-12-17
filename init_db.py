"""데이터베이스 초기화 스크립트"""

from src.database.db import init_database

if __name__ == "__main__":
    print("데이터베이스 초기화 중...")
    engine = init_database()
    print(f"✅ 데이터베이스 초기화 완료!")
    print(f"   위치: {engine.url}")

