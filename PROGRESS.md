# 구현 현황 추적

> steps.md를 기준으로 구현 진행 상황을 추적합니다.

---

## Collaboration Rules (Read this first)

These rules exist to **avoid wasting the user’s time** and to prevent accidental repo/DB damage.

- **No action without explicit approval**
  - I will **NOT** run terminal commands, edit files, create/delete files, or perform any git operation unless you explicitly say **“OK / do it / proceed”**.
- **Pre-action message (1 line, always)**
  - Before doing anything, I will post **one line**:
    - **Goal** + **exact command(s)** / **exact file(s) to change**
- **Test before commit**
  - Default workflow (unless you say otherwise):
    - **Smoke test → show results → you approve → commit**
- **Git safety**
  - **No history rewrites** (no `git reset --hard`, no `rebase`, no force-push) unless you explicitly request it and confirm you understand it can discard work.
  - **No pushing** unless you explicitly request it.
- **No guessing**
  - I will not guess ports, DB credentials, remote URLs, branch names, or “which account” settings. I will ask.
- **Minimal output**
  - I will keep answers short and actionable, and only expand explanations if you ask.

---

## 0단계 - 환경 고정

### 0-1. LLM 서버 구동 확인
- [ ] Ollama 설치 확인
- [ ] Ollama 서버 실행 확인
- [ ] `curl http://localhost:11434/api/tags` 테스트

**사용할 명령어:**
```bash
# Ollama 설치 확인
brew install ollama  # macOS

# 모델 다운로드
ollama pull llama3

# Ollama 서버 실행 (별도 터미널에서)
ollama serve

# 서버 확인
curl http://localhost:11434/api/tags
```

### 0-2. 프로젝트 초기화
- [x] Python 가상환경 생성 (`venv/`)
- [x] 디렉토리 구조 생성
  - [x] `src/llm/`
  - [x] `src/chat/`
  - [x] `src/memory/`
  - [x] `src/search/`
  - [x] `src/prompt/templates/`
  - [x] `src/database/`
- [x] `requirements.txt` 생성
- [x] `.gitignore` 생성
- [x] 패키지 설치 (`pip install -r requirements.txt`)

**사용한 명령어:**
```bash
# Python 버전 확인
python3 --version

# 가상환경 생성
python3 -m venv venv

# 디렉토리 구조 생성
mkdir -p src/llm src/chat src/memory src/search src/prompt/templates src/database

# 가상환경 활성화 및 패키지 설치
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

---

## 1단계 - LLM Service (UI, DB ❌)

### 1-1. Ollama Provider 구현
- [x] `src/llm/ollama_provider.py` 생성
- [x] `generate()` 메서드 구현
- [x] Ollama API 구조 이해 및 messages 포맷 확정
- [x] temperature / max_tokens 옵션 처리
- [x] 테스트 코드 생성 (`test_ollama.py`)
- [ ] 실제 테스트 실행 (Ollama 서버 필요)

### 1-2. LLM 추상화 계층
- [x] `src/llm/llm_provider.py` 인터페이스/추상 클래스 정의
- [x] `OllamaProvider`가 인터페이스 구현하도록 수정

**사용한 명령어:**
```bash
# 생성된 파일들
# - src/llm/llm_provider.py (LLM Provider 인터페이스)
# - src/llm/ollama_provider.py (Ollama 구현)
# - test_ollama.py (테스트 스크립트)

# 테스트 실행 (Ollama 서버 실행 후)
source venv/bin/activate
python test_ollama.py
```

**목표:** 기억 없는 챗봇 완성

---

## 2단계 - Prompt / Context 조립기 (핵심)

### 2-1. Prompt Template 정의
- [ ] `src/prompt/templates/base_system.txt` 생성
- [ ] `src/prompt/templates/search_augmented.txt` 생성

### 2-2. Context Assembler 구현
- [ ] `src/prompt/context_assembler.py` 생성
- [ ] `build_context()` 함수 구현
  - [ ] 메시지 순서 강제
  - [ ] 토큰 초과 방지
  - [ ] search 결과 삽입 위치 통제

**사용할 명령어:**
```bash
# (구현 시 추가 예정)
```

**이거 없이 프로젝트 100% 망가짐**

---

## 3단계 - Chat Manager (아직 DB ❌)

### 3-1. 단일 요청 흐름 완성
- [x] `src/chat/chat_manager.py` 생성
- [x] `ChatManager` 클래스 구현
- [x] `chat(user_message)` 메서드 구현
- [x] Context Assembler 통합
- [x] LLM Service 통합
- [x] 인터랙티브 데모 파일 생성 (`step3_chat_manager_interactive.py`)

**사용한 명령어:**
```bash
# 데모 실행
python step3_chat_manager_interactive.py
```

**목표:** "기억 없는 챗봇" 완성 (클래스 기반 구조)

---

## 4단계 - DB & Memory (여기서부터 진짜 시작)

### 4-1. DB 스키마 생성
- [x] `src/database/models.py` 생성
- [x] `Conversation` 모델 정의 (conversations 테이블)
- [x] `Message` 모델 정의 (messages 테이블)
- [x] `src/database/db.py` 생성 (DB 설정)
- [x] `init_db.py` 생성 (DB 초기화 스크립트)
- [x] DB 초기화 완료

### 4-2. Memory Manager 구현
- [x] `src/memory/memory_manager.py` 생성
- [x] `save_message()` 구현
- [x] `load_recent_messages()` 구현
- [x] `create_conversation()` 구현
- [x] `get_or_create_conversation()` 구현

**사용한 명령어:**
```bash
# DB 초기화
python init_db.py
```

**핵심:** "전부 불러오기" ❌ → "선별 + 요약" ✅

> **기억은 저장이 아니라 재주입이다**

---

## 5단계 - Chat + Memory 결합

- [x] `src/chat/chat_manager_with_db.py` 생성
- [x] ChatManagerWithDB 클래스 구현
- [x] Memory Manager 통합
- [x] `chat()` 메서드에서 DB 저장/로드 구현
- [x] 세션 관리 (conversation_id 사용)
- [x] 인터랙티브 데모 파일 생성 (`step5_chat_with_db_interactive.py`)

**사용한 명령어:**
```bash
# 데모 실행
python step5_chat_with_db_interactive.py
```

**목표:** "기억하는 것처럼 보이는 챗" 완성 (프로그램 종료 후에도 기억)

---

## 6단계 - Search Service (RAG 흉내)

### 6-1. 검색 필요 판단
- [ ] `src/search/search_service.py` 생성
- [ ] `should_search(user_message)` 구현
  - [ ] 1차: 룰 기반 (최근, 오늘, 가격, 뉴스, 2024 등)
  - [ ] 2차: LLM 판단 (선택사항)

### 6-2. 검색 결과 정제
- [ ] `search(query)` 구현 (DuckDuckGo 연동)
- [ ] 검색 결과 정제/요약
- [ ] Context에 삽입

**사용할 명령어:**
```bash
# DuckDuckGo 검색 테스트 (구현 시 추가 예정)
# python -m src.search.search_service
```

**중요:** 검색 결과 그대로 LLM에 넣지 마라

---

## 7단계 - 전체 파이프라인 완성

최종 흐름:
```
Request
 → Search 판단
 → Memory 로드
 → Context 조립
 → LLM 호출
 → 응답 저장
 → Response
```

- [ ] 모든 컴포넌트 통합
- [ ] 에러 처리
- [ ] 로깅

**사용할 명령어:**
```bash
# 전체 시스템 테스트 (구현 시 추가 예정)
# python main.py
# 또는
# python -m src.server
```

**목표:** "로컬 LLM 챗 시스템" 완성

---

## 8단계 - (선택) 고급 단계

- [ ] Streaming 응답
- [ ] Vector DB 통합
- [ ] User Profile Memory
- [ ] Tool calling
- [ ] Web UI

**위 구조가 흔들리지 않을 때만 진행**

---

## 8-추가단계 - LangChain + 외부 검색(Web Search, 키 없음 / DuckDuckGo)

- [x] `step8_langchain_web_search_agent.py` 추가 (LangChain + DuckDuckGo 검색 Tool, 키 없이)
- [x] Step8 무한 루프 방지: 기본을 Chain(1회 검색→요약)으로 변경, Agent 모드는 옵션 + iteration/time 제한
- [ ] (선택) LangChain Agent에 DBQueryTool 결합 (DB + Web 멀티툴)

**사용한/사용할 명령어:**
```bash
# 패키지 설치
./venv/bin/pip install -r requirements.txt

# Step8 실행
./venv/bin/python step8_langchain_web_search_agent.py

# 스모크 테스트(비대화형)
cat <<'EOF' | ./venv/bin/python step8_langchain_web_search_agent.py
오늘 한국 기준 USD/KRW 환율 대략 얼마야? 출처도 같이.
최신 파이썬 안정 버전 뭐야? 출처 포함.
quit
EOF
```

## 현재 상태

**진행 중:** 7-추가단계(테이블 조회) 고도화 진행 (query vs transform)

---

## 6-추가단계 - PostgreSQL 연결 (step6, 기존 SQLite 유지)

- [x] `src/database/db_postgres.py` 추가 (PostgreSQL 전용 연결 모듈)
- [x] `step6_postgresql.md` 추가 (docker-compose 메모 포함)
- [x] `step6_init_db_postgres.py` 추가 (PostgreSQL 테이블 생성)
- [x] `step6_chat_with_postgres_interactive.py` 추가 (PostgreSQL 저장/로드 챗)
- [x] `psycopg2-binary` 설치/적용

**사용한/사용할 명령어:**
```bash
# 드라이버 설치
./venv/bin/pip install psycopg2-binary

# Postgres 테이블 생성
./venv/bin/python step6_init_db_postgres.py

# Postgres 챗 실행
./venv/bin/python step6_chat_with_postgres_interactive.py
```

---

## 7-추가단계 - PostgreSQL 테이블 조회 (step7, SELECT-only)

- [x] `src/tools/db_query_tool.py` 구현 (SELECT/CTE만 실행)
- [x] `step7_chat_with_postgres_db_query_tool.py` 구현 (자연어→SQL→실행→답변)
- [x] 후속 질문 처리 고도화: LLM이 JSON으로 `query` vs `transform` 선택 (필터/조건은 query 우선)
- [x] 출력 가시성 개선(A안): 실행 SQL + 표 형태 RESULT + LLM 요약을 함께 출력

**사용한 명령어:**
```bash
./venv/bin/python step7_chat_with_postgres_db_query_tool.py

# 스모크 테스트(비대화형)
printf "가입자 정보 알려줘\n이름만 정리해서 나열해줘\n이 이름이 홍길동인 유저\nquit\n" | ./venv/bin/python step7_chat_with_postgres_db_query_tool.py

# Git(기록용)
git status --porcelain=v1
git diff --stat
git add PROGRESS.md src/tools/db_query_tool.py step7_chat_with_postgres_db_query_tool.py
git commit -m "step7: json routing + sql/result visibility"
```

**완료된 작업:**
- ✅ 프로젝트 초기화 (가상환경, 디렉토리 구조, 패키지 설치)
- ✅ LLM Provider 추상화 계층 구현
- ✅ Ollama Provider 구현 (generate 메서드, 옵션 처리)
- ✅ Prompt Template 정의 (base_system.txt, search_augmented.txt)
- ✅ Context Assembler 구현 (메시지 순서, 토큰 제한 관리)
- ✅ Chat Manager 구현 (클래스 기반 구조화)
- ✅ DB 스키마 생성 (Conversation, Message 모델)
- ✅ Memory Manager 구현 (DB 저장/로드)
- ✅ Chat Manager with DB 구현 (DB 저장/로드 통합)

**다음 작업:** 
1. 6단계: Search Service 구현 (인터넷 검색 기능)

---

## 참고사항

- 구현 순서를 절대 바꾸지 말 것: `LLM 호출 → 프롬프트 → 챗 → 메모리 → 검색 → 통합`
- ❌ DB부터 시작하지 않기
- ❌ UI부터 시작하지 않기
- ❌ 기억부터 시작하지 않기

---

## 전체 명령어 요약

### 환경 설정
```bash
# Python 버전 확인
python3 --version

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 디렉토리 구조 생성
```bash
mkdir -p src/llm src/chat src/memory src/search src/prompt/templates src/database
```

### Ollama 설정
```bash
# Ollama 설치 (macOS)
brew install ollama

# 모델 다운로드
ollama pull llama3

# 서버 실행 (별도 터미널)
ollama serve

# 서버 확인
curl http://localhost:11434/api/tags
```

### 테스트
```bash
# 가상환경 활성화 후
source venv/bin/activate
python test_ollama.py
```

