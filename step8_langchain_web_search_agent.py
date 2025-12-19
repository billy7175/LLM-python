"""
Step 8: LangChain + 외부 검색(키 없이) 데모

목표:
- LangChain을 이용해 "웹 검색 Tool"을 연결한다.
- 키 없이 가능한 DuckDuckGo 검색(`duckduckgo-search`)을 사용한다.
- 기존 Step1~7 코드에는 영향 없이, step8 단일 스크립트로만 제공한다.

전제:
- Ollama 서버 실행 중: `ollama serve`
- (선택) .env로 모델 지정: OLLAMA_MODEL=llama3

중요(현업 기준 UX):
- 기본 모드는 **Chain(1회 검색 → 요약)** 입니다. (무한 루프 방지)
- 에이전트(ReAct)는 옵션으로만 제공합니다. (STEP8_MODE=agent)
"""

from __future__ import annotations

import os
import warnings
from typing import List

from dotenv import load_dotenv
from duckduckgo_search import DDGS


def _build_llm():
    """
    LangChain Ollama Chat 모델을 생성합니다.
    - 기본 모델: llama3
    - base_url은 환경에 따라 필요할 수 있으나, 기본값은 Ollama 로컬을 가정합니다.
    """
    model = os.getenv("OLLAMA_MODEL", "llama3")
    base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST")  # 둘 중 하나를 허용

    try:
        # 권장: langchain-ollama
        from langchain_ollama import ChatOllama  # type: ignore

        if base_url:
            return ChatOllama(model=model, base_url=base_url, temperature=0.0)
        return ChatOllama(model=model, temperature=0.0)
    except Exception:
        # fallback: 일부 버전에서 community 쪽에 있을 수 있음
        from langchain_community.chat_models import ChatOllama  # type: ignore

        if base_url:
            return ChatOllama(model=model, base_url=base_url, temperature=0.0)
        return ChatOllama(model=model, temperature=0.0)


def _web_search(query: str, max_results: int = 5) -> str:
    """
    DuckDuckGo 검색 결과를 사람이 읽기 좋은 텍스트로 반환합니다.
    - 키 불필요
    - 운영에서는 캐시/도메인 정책/타임아웃을 추가하는 것을 권장
    """
    q = (query or "").strip()
    if not q:
        return "(empty query)"

    items: List[str] = []
    with DDGS() as ddgs:
        # 버전 차이로 파라미터 지원이 다를 수 있어, 우선 옵션 포함 시도 후 실패하면 폴백합니다.
        try:
            results = ddgs.text(
                q,
                max_results=int(max_results),
                region=os.getenv("DDG_REGION", "kr-kr"),
                safesearch=os.getenv("DDG_SAFESEARCH", "moderate"),
                timelimit=os.getenv("DDG_TIMELIMIT", "d"),
            )
        except TypeError:
            results = ddgs.text(q, max_results=int(max_results))

        for r in results:
            title = (r.get("title") or "").strip()
            href = (r.get("href") or "").strip()
            body = (r.get("body") or "").strip()
            line = f"- {title}\n  - url: {href}\n  - snippet: {body}"
            items.append(line)

    if not items:
        return "(no results)"
    return "\n".join(items)


def _build_chain():
    llm = _build_llm()

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda

    # 1) 검색 쿼리 생성 (LLM이 검색어를 더 잘 만들게)
    query_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 웹 검색 쿼리 생성기야. 사용자 질문을 바탕으로 검색에 적합한 '짧은 검색어' 1줄만 출력해. "
                "따옴표/마크다운/추가 설명 금지. (예: USD KRW exchange rate today)",
            ),
            ("user", "{question}"),
        ]
    )

    # 2) 검색 결과 기반 답변
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 웹 검색 결과를 바탕으로 답변하는 도우미야.\n"
                "- 반드시 한국어로 답해.\n"
                "- 아래 [검색결과]에서 확인 가능한 내용만 사용해.\n"
                "- 답변 끝에 사용한 출처 URL을 2개 이상 bullet로 나열해.\n"
                "- 수치가 출처마다 다르면 '대략'으로 설명하고, 기준 시간을 함께 말해.\n",
            ),
            ("user", "질문: {question}\n\n[검색결과]\n{search_results}"),
        ]
    )

    debug = os.getenv("STEP8_DEBUG", "0") == "1"

    def _chain_invoke(inp: dict) -> str:
        question = (inp.get("input") or "").strip()
        if not question:
            return "(empty input)"

        # 검색어 생성
        qmsg = query_prompt.invoke({"question": question})
        qout = llm.invoke(qmsg)
        query = (getattr(qout, "content", str(qout)) or "").strip()
        if not query:
            query = question

        # 1차 검색
        search_results = _web_search(query, max_results=5)

        # 2차 폴백 검색(최소한의 품질 개선): 환율/버전 등에서 가끔 엉뚱한 결과가 섞이는 경우가 있어 보조 검색을 합칩니다.
        fallback_query = f"{query} xe wise google finance"
        if fallback_query != query:
            search_results2 = _web_search(fallback_query, max_results=5)
            if search_results2 and search_results2 != "(no results)":
                search_results = search_results + "\n\n[추가 검색]\n" + search_results2

        if debug:
            print("\n[DEBUG] search_query:", query)
            print("\n[DEBUG] search_results_preview:\n", search_results[:800])

        amsg = answer_prompt.invoke({"question": question, "search_results": search_results})
        aout = llm.invoke(amsg)
        return getattr(aout, "content", str(aout))

    return RunnableLambda(_chain_invoke)


def _build_agent():
    """
    옵션(데모용): ReAct Agent
    - 무한 루프 방지를 위해 iterations/time 제한을 강제합니다.
    """
    llm = _build_llm()

    # LangChain Tool 래핑
    try:
        from langchain_core.tools import tool
    except Exception:
        from langchain.tools import tool  # type: ignore

    @tool("web_search")
    def web_search_tool(query: str) -> str:
        """키 없이 DuckDuckGo로 웹을 검색합니다. 결과에는 URL이 포함됩니다."""
        return _web_search(query, max_results=5)

    tools = [web_search_tool]

    # ReAct 스타일 Agent (텍스트 기반 tool-use)
    # 버전 호환을 위해 initialize_agent를 우선 사용합니다.
    try:
        from langchain.agents import AgentType, initialize_agent

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=(os.getenv("LANGCHAIN_VERBOSE", "0") == "1"),
            handle_parsing_errors=True,
            max_iterations=int(os.getenv("LANGCHAIN_MAX_ITERATIONS", "4")),
            max_execution_time=int(os.getenv("LANGCHAIN_MAX_EXECUTION_TIME", "25")),
        )
        return agent
    except Exception:
        # Agent가 깨지면 Chain으로 폴백
        return _build_chain()


def _agent_invoke(agent, user_text: str) -> str:
    """
    Agent/Chain 버전 차이를 흡수하면서 호출합니다.
    """
    # 사용자 요청에 "출처 포함/한국어"를 강제(운영에서 정책으로 분리 가능)
    augmented = user_text.strip() + "\n\n답변은 한국어로. 웹 검색을 사용했다면 출처 URL을 함께 포함해."

    # Runnable 기반
    if hasattr(agent, "invoke"):
        try:
            res = agent.invoke({"input": augmented})
            if isinstance(res, dict) and "output" in res:
                return str(res["output"])
            return str(res)
        except Exception:
            pass

    # legacy run()
    if hasattr(agent, "run"):
        return str(agent.run(augmented))

    return "(agent invoke failed)"


def main():
    load_dotenv()

    # noisy warnings suppress (사용자 UX 목적)
    warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")
    warnings.filterwarnings("ignore", message="This package \\(`duckduckgo_search`\\) has been renamed.*")
    warnings.filterwarnings("ignore", message="LangChain agents will continue to be supported.*")

    print("=" * 60)
    print("Step8: LangChain + Web Search (DuckDuckGo, 키 없음)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 60)

    mode = os.getenv("STEP8_MODE", "chain").strip().lower()
    if mode not in ("chain", "agent"):
        mode = "chain"

    runner = _build_agent() if mode == "agent" else _build_chain()
    print(f"(mode={mode})")

    while True:
        user_input = input("\n[당신]: ").strip()
        if user_input.lower() in ["quit", "exit", "종료", "q"]:
            print("\n안녕히가세요!")
            break
        if not user_input:
            continue

        try:
            answer = _agent_invoke(runner, user_input)
        except Exception as e:
            answer = f"(에러) {e}"

        print(f"\n[봇]: {answer}")


if __name__ == "__main__":
    main()


