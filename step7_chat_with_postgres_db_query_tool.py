"""
Step 7: PostgreSQL + DB 테이블 조회 (자연어 → SQL → 실행 → 결과 기반 답변)

개발 단계 목표:
- "성적이 80점 아래인 사람들 조회해", "서비스 가입 수 알려줘" 같은 요청을
  PostgreSQL에서 SELECT로 조회하고 결과를 기반으로 답변한다.

중요:
- 기존 SQLite 기반 step들은 그대로 둔다.
- step7은 step6의 PostgreSQL 연결(`src/database/db_postgres.py`)을 사용한다.
- 안전을 위해 SQL은 SELECT/CTE(WITH)만 실행한다. (DELETE/DROP 등 차단)
"""

from typing import List, Optional

from dotenv import load_dotenv

from src.database.db_postgres import get_engine_postgres, get_session_postgres
from src.llm.ollama_provider import OllamaProvider
from src.memory.memory_manager import MemoryManager
from src.tools.db_query_tool import (
    DBQueryTool,
    QueryResult,
    extract_first_sql_statement,
    is_safe_select_sql,
)


SQL_SYSTEM_PROMPT = """You are a PostgreSQL SQL generator.
Return ONLY ONE SQL statement that is safe to run as READ-ONLY (SELECT or WITH ... SELECT).
Do NOT use INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE.
Do NOT include multiple statements.
Do NOT include markdown/code fences. Output plain SQL only.
If possible, include a LIMIT clause.

If you cannot write a correct SELECT based on the schema, return exactly:
NO_SQL
"""


ANSWER_SYSTEM_PROMPT = """You are a helpful assistant.
Answer using the provided database query results only.
If the result is empty, say so.
If the question cannot be answered from the results, say you cannot answer from the results.
"""

def _normalize_col_name(name: str) -> str:
    return (name or "").strip().lower()


def _infer_requested_columns(user_request: str) -> List[str]:
    """
    후속 요청에서 사용자가 원하는 컬럼을 간단히 추론합니다.
    예) "이름만" -> ["name"], "이메일만" -> ["email"]
    """
    txt = (user_request or "").strip().lower()
    cols: List[str] = []

    # 한국어/영어 간단 매핑
    mapping = {
        "이름": "name",
        "name": "name",
        "메일": "email",
        "이메일": "email",
        "email": "email",
        "id": "id",
    }

    for k, v in mapping.items():
        if k in txt and v not in cols:
            cols.append(v)

    return cols


def _format_single_column_list(values: List[object], prefix: str = "- ") -> str:
    cleaned: List[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        cleaned.append(s)
    if not cleaned:
        return "(0 rows)"
    return "\n".join([f"{prefix}{v}" for v in cleaned])


def _generate_sql(llm: OllamaProvider, schema_text: str, user_request: str) -> str:
    messages = [
        {"role": "system", "content": f"{SQL_SYSTEM_PROMPT}\n\nSchema:\n{schema_text}"},
        {"role": "user", "content": user_request},
    ]
    sql = llm.generate(messages, temperature=0.0)
    return (sql or "").strip()

def _regenerate_sql_with_error(llm: OllamaProvider, schema_text: str, user_request: str, error_reason: str) -> str:
    messages = [
        {"role": "system", "content": f"{SQL_SYSTEM_PROMPT}\n\nSchema:\n{schema_text}"},
        {
            "role": "user",
            "content": (
                f"Request: {user_request}\n\n"
                f"Previous attempt failed due to: {error_reason}\n"
                "Return ONE valid read-only SQL (SELECT/WITH) only."
            ),
        },
    ]
    sql = llm.generate(messages, temperature=0.0)
    return (sql or "").strip()


def _final_answer(llm: OllamaProvider, user_request: str, sql: Optional[str], result_text: str) -> str:
    context = []
    if sql:
        context.append(f"[SQL]\n{sql}")
    context.append(f"[DB_RESULT]\n{result_text}")
    messages = [
        {"role": "system", "content": f"{ANSWER_SYSTEM_PROMPT}\n\n" + "\n\n".join(context)},
        {"role": "user", "content": user_request},
    ]
    return llm.generate(messages, temperature=0.2).strip()


def main():
    load_dotenv()

    print("=" * 60)
    print("로컬 LLM 챗 (PostgreSQL + DB 조회 Tool)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)

    # Postgres 세션 준비
    engine = get_engine_postgres()
    pg_session = get_session_postgres(engine=engine)
    memory_manager = MemoryManager(session=pg_session)

    # 대화 세션 (기본값)
    session_id = "default"
    conversation = memory_manager.get_or_create_conversation(session_id)

    tool = DBQueryTool(engine=engine)
    llm = OllamaProvider()

    # 스키마 요약 (초기 1회)
    schema_text = tool.schema_summary_text(schema="public", max_tables=30, max_cols_per_table=25)
    last_result: Optional[QueryResult] = None
    last_sql: Optional[str] = None

    while True:
        user_input = input("\n[당신]: ").strip()
        if user_input.lower() in ["quit", "exit", "종료", "q"]:
            print("\n👋 안녕히가세요!")
            break
        if not user_input:
            continue

        # 후속 질문: 직전 DB 결과에서 "특정 컬럼만" 뽑아달라는 요청 처리
        # 예) "이름만 정리해서 나열해줘"
        requested_cols = _infer_requested_columns(user_input)
        if last_result is not None and requested_cols:
            cols_lower = [_normalize_col_name(c) for c in last_result.columns]
            # 요청한 컬럼이 직전 결과에 포함되면 DB 재조회 없이 바로 응답
            hit = [c for c in requested_cols if c in cols_lower]
            if hit:
                # 우선 첫 번째 요청 컬럼만 처리 (개발 단계 단순화)
                col = hit[0]
                idx = cols_lower.index(col)
                values = [row[idx] for row in last_result.rows]
                answer_text = _format_single_column_list(values)
                print(f"\n[봇]:\n{answer_text}")
                memory_manager.save_message(conversation.id, "assistant", answer_text)
                continue

        # 메타 질문(“DB 조회 가능해?”)은 DB 실행 없이 안내만 제공
        lowered = user_input.replace(" ", "").lower()
        if ("조회가능" in lowered) or ("db조회" in lowered and "가능" in lowered):
            msg = (
                "네. PostgreSQL의 다른 테이블도 SELECT로 조회해서 답할 수 있습니다.\n"
                "예) \"서비스 가입 수 알려줘\", \"성적이 80점 아래인 사람들 조회해\".\n"
                "필요하면 테이블/컬럼 스키마를 기반으로 SQL을 생성해 조회합니다."
            )
            print(f"\n[봇]: {msg}")
            memory_manager.save_message(conversation.id, "assistant", msg)
            continue

        # 사용자 메시지 저장
        memory_manager.save_message(conversation.id, "user", user_input)

        # 1) SQL 생성
        raw_sql = _generate_sql(llm, schema_text=schema_text, user_request=user_input)
        sql = extract_first_sql_statement(raw_sql)

        # 추출 결과가 없으면 NO_SQL 취급
        if not sql or raw_sql.strip().upper() == "NO_SQL":
            answer = _final_answer(llm, user_input, sql=None, result_text="(NO_SQL)")
            print(f"\n[봇]: {answer}")
            memory_manager.save_message(conversation.id, "assistant", answer)
            continue

        # 1-1) 안전성 체크 (실패 시 1회 재시도)
        ok, reason = is_safe_select_sql(sql)
        if not ok:
            raw_retry = _regenerate_sql_with_error(llm, schema_text, user_input, error_reason=reason)
            sql_retry = extract_first_sql_statement(raw_retry)
            if sql_retry:
                sql = sql_retry
                ok2, reason2 = is_safe_select_sql(sql)
                if not ok2:
                    # 사용자에게는 DB 결과 기반 답변이 불가능하다고 알려줌 (디버그는 콘솔로)
                    print("\n[DEBUG] SQL rejected")
                    print("[DEBUG] raw_llm_output:", raw_sql)
                    print("[DEBUG] extracted_sql:", sql)
                    print("[DEBUG] reason:", reason2)
                    answer = _final_answer(llm, user_input, sql=sql, result_text=f"(SQL rejected: {reason2})")
                    print(f"\n[봇]: {answer}")
                    memory_manager.save_message(conversation.id, "assistant", answer)
                    continue
            else:
                print("\n[DEBUG] SQL rejected (no extractable retry)")
                print("[DEBUG] raw_llm_output:", raw_sql)
                print("[DEBUG] reason:", reason)
                answer = _final_answer(llm, user_input, sql=None, result_text=f"(SQL rejected: {reason})")
                print(f"\n[봇]: {answer}")
                memory_manager.save_message(conversation.id, "assistant", answer)
                continue

        # 2) SQL 실행 (SELECT-only)
        try:
            result = tool.run_select(sql, max_rows=50)
            result_text = tool.format_result(result)
        except Exception as e:
            # 디버그 정보는 콘솔에 그대로
            print("\n[DEBUG] SQL execution failed")
            print("[DEBUG] extracted_sql:", sql)
            print("[DEBUG] error:", e)
            answer = _final_answer(
                llm,
                user_input,
                sql=sql,
                result_text=f"(SQL 실행 실패: {e})",
            )
            print(f"\n[봇]: {answer}")
            memory_manager.save_message(conversation.id, "assistant", answer)
            continue

        # 3) 결과 기반 답변
        answer = _final_answer(llm, user_input, sql=sql, result_text=result_text)
        print(f"\n[봇]: {answer}")

        # 후속 요청을 위해 직전 결과를 기억 (프로세스 내 메모리)
        last_result = result
        last_sql = sql

        # 응답 저장
        memory_manager.save_message(conversation.id, "assistant", answer)


if __name__ == "__main__":
    main()


