"""
Step 6: PostgreSQL 테이블 초기화 (기존 SQLite 방식 유지)

이 스크립트는 step6에서만 PostgreSQL에 테이블을 생성합니다.
기존 `init_db.py`(SQLite)는 그대로 유지합니다.

필요 조건:
- Postgres 컨테이너가 실행 중이어야 함
- psycopg2-binary 설치 필요 (requirements.txt에서 주석 해제 후 설치 권장)

환경변수 예시:
- POSTGRES_USER=postgres
- POSTGRES_PASSWORD=postgres
- POSTGRES_DB=nestjs_db
- POSTGRES_HOST=localhost
- POSTGRES_PORT=5432
또는:
- STEP6_POSTGRES_DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/nestjs_db"
"""

from dotenv import load_dotenv

from src.database.db_postgres import init_database_postgres


if __name__ == "__main__":
    load_dotenv()
    print("PostgreSQL 테이블 초기화 중...")
    engine = init_database_postgres()
    print("✅ PostgreSQL 테이블 초기화 완료!")
    print(f"   URL: {engine.url}")


