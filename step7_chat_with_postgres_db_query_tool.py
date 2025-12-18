"""
Step 7: PostgreSQL + DB 테이블 조회 (자연어 → (query|transform) → 실행/가공 → 답변)

목표(현업 기준에 더 가깝게):
- 사용자 입력을 매번 "query(DB 재조회)" 또는 "transform(직전 결과 가공)"으로 분기한다.
- 분기는 LLM이 **JSON으로 명시적으로 결정**한다. (query vs transform)
- query는 SELECT-only로 실행하고, transform은 직전 결과를 가공한다.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from src.database.db_postgres import get_engine_postgres, get_session_postgres
from src.llm.ollama_provider import OllamaProvider
from src.memory.memory_manager import MemoryManager
from src.tools.db_query_tool import (
    DBQueryTool,
    QueryResult,
    extract_first_sql_statement,
    is_safe_select_sql,
    make_count_sql_from_select,
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


ANSWER_SYSTEM_PROMPT = """당신은 도움이 되는 어시스턴트입니다.
아래 제공된 DB 조회 결과(DB_RESULT)만 근거로 답변하세요.
- 결과가 비어있으면 "결과가 없습니다"라고 말하세요.
- 결과만으로 답을 확정할 수 없으면 "DB 결과만으로는 답변할 수 없습니다"라고 말하세요.
- 가능한 한 한국어로 간결하게 답변하세요.
"""


ROUTER_SYSTEM_PROMPT = """당신은 DB 질의 라우터입니다.
사용자 요청을 보고 아래 중 하나를 JSON으로 선택하세요.

1) query: DB를 다시 조회해야 하는 경우 (필터/조건/집계/정확한 카운트/새로운 조건 추가)
2) transform: 직전 DB 결과를 가공하면 되는 경우 (표현 변경, 특정 컬럼만 보기, 직전 결과의 개수 등)

출력은 반드시 JSON 1개만. 다른 텍스트 금지.

JSON 스키마:
- query:
  {"action":"query"}
- transform (컬럼만 보기):
  {"action":"transform","operation":"pick_column","column":"name"}
- transform (직전 결과 기반 개수):
  {"action":"transform","operation":"count_last"}

규칙(중요):
- "…인/…아래/…이상/…미만/…같은" 등 조건/필터가 있으면 query가 우선입니다.
- "이름만/이메일만/ID만"처럼 출력만 바꾸는 요청이면 transform이 우선입니다.
"""


@dataclass
class RouteDecision:
    action: str  # "query" | "transform"
    operation: Optional[str] = None  # for transform
    column: Optional[str] = None  # for transform pick_column

def _normalize_col_name(name: str) -> str:
    return (name or "").strip().lower()


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

def _extract_json_object(text_out: str) -> Optional[Dict[str, Any]]:
    """
    LLM 출력에서 JSON object를 최대한 추출합니다.
    """
    if not text_out:
        return None
    s = text_out.strip()
    # 코드펜스 제거
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
    if m:
        s = m.group(1).strip()

    # 첫 { ... } 블록을 찾아 파싱 시도
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = s[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _route_action(
    llm: OllamaProvider,
    user_request: str,
    last_result: Optional[QueryResult],
    last_sql: Optional[str],
) -> RouteDecision:
    """
    현업식(가까운) 분기: LLM이 JSON으로 query/transform을 명시.
    """
    last_cols = []
    last_rows = 0
    if last_result is not None:
        last_cols = last_result.columns
        last_rows = len(last_result.rows)

    messages = [
        {
            "role": "system",
            "content": ROUTER_SYSTEM_PROMPT
            + "\n\n"
            + "Context:\n"
            + f"- last_sql_present: {bool(last_sql)}\n"
            + f"- last_result_rows: {last_rows}\n"
            + f"- last_result_columns: {last_cols}\n",
        },
        {"role": "user", "content": user_request},
    ]
    raw = llm.generate(messages, temperature=0.0)
    obj = _extract_json_object(raw or "")

    action = (obj or {}).get("action", "query")
    operation = (obj or {}).get("operation")
    column = (obj or {}).get("column")

    if action not in ("query", "transform"):
        action = "query"

    # 최소 안전장치: 필터/조건처럼 보이는 문장은 query 우선(LLM 오판 방지)
    cond_hints = ("인 ", "인유저", "인 사용자", "아래", "이상", "미만", "같은", "where", "=")
    if action == "transform" and any(h in user_request for h in cond_hints):
        action = "query"
        operation = None
        column = None

    return RouteDecision(action=action, operation=operation, column=column)


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

def _extract_table_name_from_korean_question(text: str) -> Optional[str]:
    """
    예) "users 테이블 있어?" -> "users"
    """
    if not text:
        return None
    m = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*테이블", text)
    if not m:
        return None
    return m.group(1)


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
    schema_text = tool.schema_summary_text(schema="public", max_tables=60, max_cols_per_table=25)
    last_result: Optional[QueryResult] = None
    last_sql: Optional[str] = None

    while True:
        user_input = input("\n[당신]: ").strip()
        if user_input.lower() in ["quit", "exit", "종료", "q"]:
            print("\n안녕히가세요!")
            break
        if not user_input:
            continue

        # 스키마 질문: "<table> 테이블 있어?"는 LLM을 거치지 않고 information_schema 기반으로 즉시 응답
        table_name = _extract_table_name_from_korean_question(user_input)
        if table_name and ("있어" in user_input or "존재" in user_input):
            tables = tool.list_tables(schema="public", limit=500)
            exists = table_name in tables
            msg = f"{'있습니다' if exists else '없습니다'}. (public.{table_name})"
            print(f"\n[봇]: {msg}")
            memory_manager.save_message(conversation.id, "assistant", msg)
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

        # 라우팅: query vs transform (LLM JSON)
        route = _route_action(llm, user_input, last_result=last_result, last_sql=last_sql)

        # transform 처리
        if route.action == "transform":
            if route.operation == "count_last":
                if last_sql:
                    try:
                        count_sql = make_count_sql_from_select(last_sql)
                        result = tool.run_select(count_sql, max_rows=5)
                        result_text = tool.format_result(result)
                        print("\n[SQL]")
                        print(count_sql)
                        print("\n[RESULT]")
                        print(result_text)
                        answer = _final_answer(llm, user_input, sql=count_sql, result_text=result_text)
                        print(f"\n[봇]: {answer}")
                        last_result = result
                        last_sql = count_sql
                        memory_manager.save_message(conversation.id, "assistant", answer)
                        continue
                    except Exception as e:
                        answer = _final_answer(llm, user_input, sql=last_sql, result_text=f"(COUNT 변환 실패: {e})")
                        print(f"\n[봇]: {answer}")
                        memory_manager.save_message(conversation.id, "assistant", answer)
                        continue
                if last_result is not None:
                    answer_text = f"직전 결과 기준 {len(last_result.rows)}개입니다."
                    print(f"\n[봇]: {answer_text}")
                    memory_manager.save_message(conversation.id, "assistant", answer_text)
                    continue

            if route.operation == "pick_column":
                if last_result is None:
                    # 직전 결과가 없으면 query로 폴백
                    route = RouteDecision(action="query")
                else:
                    cols_lower = [_normalize_col_name(c) for c in last_result.columns]
                    col = (route.column or "").strip().lower()
                    # LLM이 한국어로 컬럼을 내보내는 경우를 최소 보정
                    col_alias = {
                        "이름": "name",
                        "성명": "name",
                        "메일": "email",
                        "이메일": "email",
                        "아이디": "id",
                    }
                    col = col_alias.get(col, col)
                    if not col:
                        col = "name"
                    if col not in cols_lower:
                        # 못 찾으면 query로 폴백
                        route = RouteDecision(action="query")
                    else:
                        idx = cols_lower.index(col)
                        values = [row[idx] for row in last_result.rows]
                        answer_text = _format_single_column_list(values)
                        print("\n[TRANSFORM]")
                        print(f"operation=pick_column column={col} (DB 재조회 없음)")
                        print(f"\n[봇]:\n{answer_text}")
                        memory_manager.save_message(conversation.id, "assistant", answer_text)
                        continue

        # 1) SQL 생성
        # 후속 요청일 가능성이 있으면 이전 SQL을 힌트로 제공(재가공/재조회 유도)
        hint = ""
        if last_sql:
            hint = f"\n\nPrevious SQL (for follow-up context):\n{last_sql}\n"

        raw_sql = _generate_sql(llm, schema_text=schema_text + hint, user_request=user_input)
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
        print("\n[SQL]")
        print(sql)
        print("\n[RESULT]")
        print(result_text)
        answer = _final_answer(llm, user_input, sql=sql, result_text=result_text)
        print(f"\n[봇]: {answer}")

        # 후속 요청을 위해 직전 결과를 기억 (프로세스 내 메모리)
        last_result = result
        last_sql = sql

        # 응답 저장
        memory_manager.save_message(conversation.id, "assistant", answer)


if __name__ == "__main__":
    main()


