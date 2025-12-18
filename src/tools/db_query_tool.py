"""DB Query Tool (step7)

개발 단계 목적:
- 자연어 → SQL(SELECT) → 실행 → 결과 기반 답변을 만들기 위한 "조회 도구" 제공
- 현재는 안전을 위해 **SELECT/CTE(WITH)만 허용**합니다.

주의:
- 복잡한 SQL 파싱을 하지 않고, 단순한 규칙 기반 검증을 합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine


_BANNED_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "commit",
    "rollback",
    "vacuum",
    "analyze",
    "call",
    "do",
)

_COUNT_HINT_KEYWORDS = (
    "count",
    "how many",
    "몇명",
    "몇 명",
    "몇개",
    "몇 개",
    "개수",
    "수량",
    "총",
)


def strip_trailing_limit(sql: str) -> str:
    """
    SQL 끝에 붙은 LIMIT 절을 단순 제거합니다.
    (정교한 파서가 아닌 개발용 유틸)
    """
    if not sql:
        return ""
    s = sql.strip().rstrip(";").strip()
    # 마지막 LIMIT n 제거 (단순 패턴)
    s = re.sub(r"\s+limit\s+\d+\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()


def make_count_sql_from_select(select_sql: str) -> str:
    """
    기존 SELECT를 서브쿼리로 감싸 COUNT(*)로 바꿉니다.
    """
    base = strip_trailing_limit(select_sql)
    return f"SELECT COUNT(*) AS count FROM (\n{base}\n) AS t"


def looks_like_count_request(user_text: str) -> bool:
    if not user_text:
        return False
    t = user_text.strip().lower()
    return any(k in t for k in _COUNT_HINT_KEYWORDS)


def extract_first_sql_statement(llm_output: str) -> str:
    """
    LLM 출력에서 실행 가능한 "첫 번째 SQL(SELECT/WITH)"만 최대한 추출합니다.
    - ```sql ... ``` 코드블록 우선
    - 아니면 본문에서 첫 SELECT/WITH부터 시작해서 첫 세미콜론 전까지
    """
    if not llm_output:
        return ""

    text_out = llm_output.strip()

    # fenced code block 우선
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text_out, flags=re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
    else:
        candidate = text_out

    # 첫 SELECT/WITH 위치부터 자르기
    m2 = re.search(r"\b(select|with)\b", candidate, flags=re.IGNORECASE)
    if not m2:
        return ""
    candidate = candidate[m2.start() :].strip()

    # 첫 세미콜론까지만
    semi = candidate.find(";")
    if semi != -1:
        candidate = candidate[:semi].strip()

    return candidate.strip()


def _strip_sql_comments(sql: str) -> str:
    # -- line comments
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    # /* block comments */
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def _split_statements(sql: str) -> List[str]:
    # 매우 단순한 세미콜론 기반 분리 (멀티 스테이트먼트 방지 목적)
    parts = [p.strip() for p in sql.split(";")]
    return [p for p in parts if p]


def is_safe_select_sql(sql: str) -> Tuple[bool, str]:
    """
    Returns:
      (is_safe, reason)
    """
    if not sql or not sql.strip():
        return False, "empty_sql"

    raw = sql.strip()
    cleaned = _strip_sql_comments(raw).strip()

    # 멀티 스테이트먼트 금지
    stmts = _split_statements(cleaned)
    if len(stmts) != 1:
        return False, "multiple_statements_not_allowed"

    normalized = re.sub(r"\s+", " ", stmts[0]).strip().lower()
    if not (normalized.startswith("select ") or normalized.startswith("with ")):
        return False, "only_select_or_with_allowed"

    # 위험 키워드 포함 금지 (단순 방어)
    for kw in _BANNED_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", normalized):
            return False, f"banned_keyword:{kw}"

    return True, "ok"


def ensure_limit(sql: str, max_rows: int) -> str:
    cleaned = _strip_sql_comments(sql).strip()
    stmts = _split_statements(cleaned)
    stmt = stmts[0].strip()

    # 이미 LIMIT이 있으면 그대로 둠
    if re.search(r"\blimit\b", stmt, flags=re.IGNORECASE):
        return stmt

    return f"{stmt}\nLIMIT {int(max_rows)}"


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[List[Any]]


class DBQueryTool:
    def __init__(self, engine: Engine):
        self.engine = engine

    def list_tables(self, schema: str = "public", limit: int = 200) -> List[str]:
        sql = text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            LIMIT :limit
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"schema": schema, "limit": int(limit)}).fetchall()
        return [r[0] for r in rows]

    def list_columns(self, table_name: str, schema: str = "public") -> List[Tuple[str, str]]:
        sql = text(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
            ORDER BY ordinal_position
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(sql, {"schema": schema, "table": table_name}).fetchall()
        return [(r[0], r[1]) for r in rows]

    def schema_summary_text(self, schema: str = "public", max_tables: int = 30, max_cols_per_table: int = 25) -> str:
        tables = self.list_tables(schema=schema, limit=max_tables)
        lines: List[str] = []
        for t in tables:
            cols = self.list_columns(t, schema=schema)[:max_cols_per_table]
            cols_str = ", ".join([f"{c}:{dt}" for c, dt in cols])
            lines.append(f"- {schema}.{t}: {cols_str}")
        if not lines:
            return "(no tables found)"
        return "\n".join(lines)

    def run_select(self, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: int = 50) -> QueryResult:
        ok, reason = is_safe_select_sql(sql)
        if not ok:
            raise ValueError(f"unsafe_sql:{reason}")

        safe_sql = ensure_limit(sql, max_rows=max_rows)
        with self.engine.connect() as conn:
            result = conn.execute(text(safe_sql), params or {})
            cols = list(result.keys())
            fetched = result.fetchmany(size=max_rows)
        rows = [list(r) for r in fetched]
        return QueryResult(columns=cols, rows=rows)

    @staticmethod
    def format_result(result: QueryResult, max_cell_chars: int = 200) -> str:
        if not result.columns:
            return "(no columns)"
        if not result.rows:
            return "(0 rows)"

        def _cell(v: Any) -> str:
            s = "" if v is None else str(v)
            s = s.replace("\n", "\\n")
            if len(s) > max_cell_chars:
                s = s[: max_cell_chars - 3] + "..."
            return s

        header = " | ".join(result.columns)
        sep = " | ".join(["---"] * len(result.columns))
        body_lines = [" | ".join(_cell(v) for v in row) for row in result.rows]
        return "\n".join([header, sep, *body_lines])


