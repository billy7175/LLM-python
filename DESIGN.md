# 로컬 LLM 시스템 설계 문서 (보완판)

> **중요 전제**
>
> * LLM은 상태를 가지지 않는다 (기억하지 않는다)
> * 모든 기억은 **시스템이 관리하여 매 요청마다 재주입**한다
> * 인터넷 검색은 **LLM이 하는 행위가 아니라 시스템이 수행한 결과를 LLM이 읽는 구조**다

---

## 1. 개요

본 문서는 **로컬에서 실행되는 LLM 기반 대화 시스템**의 설계를 정의한다.
시스템은 다음을 목표로 한다.

* 로컬 LLM 실행 (Ollama 등)
* 사용자 대화 기록을 **기억처럼 동작**하게 관리
* 필요 시 인터넷 검색 결과를 활용한 응답 생성

프라이버시를 최우선으로 하며, 모든 핵심 데이터는 로컬에서 처리된다.

---

## 2. 요구사항 정의

### 2.1 기능 요구사항

* 로컬 LLM 실행 및 추론
* 대화 세션 기반 메시지 관리
* 단기/장기 메모리 전략 적용
* 인터넷 검색 결과를 활용한 응답 생성

### 2.2 비기능 요구사항

* **프라이버시**: 대화 및 검색 데이터는 로컬 저장
* **성능**: 컨텍스트 윈도우 및 검색 최소화
* **확장성**: LLM, 검색, 메모리 전략 교체 가능 구조

---

## 3. 핵심 개념 정리 (중요)

### 3.1 LLM 메모리 개념

LLM은 다음을 **기억하지 않는다**:

* 이전 대화
* 사용자 정보
* 세션 상태

따라서 시스템은 다음 역할을 수행해야 한다:

* **Short-term Memory**: 최근 N개 메시지
* **Long-term Memory**: 요약된 과거 대화 또는 벡터 검색 결과
* **Context Assembler**: 어떤 정보를 LLM에게 다시 넣을지 결정

---

### 3.2 검색 개념

* LLM은 인터넷을 직접 조회하지 않는다
* 검색은 **Search Service**가 수행
* LLM은 검색 결과를 **문서처럼 입력받아 추론**한다

---

## 4. 시스템 아키텍처

```
┌───────────────────────────────────────────────┐
│                사용자 인터페이스               │
│          (CLI / Web UI / API Server)          │
└───────────────────┬───────────────────────────┘
                    │
┌───────────────────▼───────────────────────────┐
│                Chat Manager                   │
│  - 세션 관리                                   │
│  - 메시지 저장                                 │
│  - 메모리 전략 적용                            │
└───────────────────┬───────────────────────────┘
                    │
┌───────────────────▼───────────────────────────┐
│           Context Assembler (중요)             │
│  - 메시지 선택                                 │
│  - 검색 결과 삽입 위치 결정                   │
│  - 프롬프트 구성                               │
└───────────────────┬───────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼─────────┐
│  LLM Service   │    │ Search Service   │
│ (Ollama 등)   │    │ (DuckDuckGo 등)  │
└───────┬────────┘    └────────┬─────────┘
        │                       │
┌───────▼────────┐    ┌────────▼─────────┐
│  RDB (메시지)  │    │ Vector DB (옵션) │
└────────────────┘    └──────────────────┘
```

---

## 5. 컴포넌트 설계

### 5.1 Chat Manager

**역할**

* 대화 세션 생성/관리
* 메시지 저장
* 메모리 전략 적용

**책임**

* LLM에게 직접 메시지를 보내지 않음
* Context Assembler에 필요한 데이터 제공

---

### 5.2 Context Assembler (핵심 컴포넌트)

**역할**

* LLM 입력 메시지 구성

**주요 기능**

* 최근 N개 메시지 선택
* 장기 메모리 요약 삽입
* 검색 결과 삽입
* system / user / assistant 역할 구성
* 컨텍스트 길이 초과 방지

---

### 5.3 LLM Service

**역할**

* 로컬 LLM 실행 및 응답 생성

**프로바이더 패턴**

* OllamaProvider
* TransformersProvider

**관리 옵션**

* temperature
* max_tokens
* stop
* stream 여부

---

### 5.4 Search Service

**역할**

* 인터넷 검색 수행

**검색 판단 전략 (권장)**

1. **룰 기반 1차 판단**

   * 날짜/최신성 키워드
   * 시사/가격/뉴스

2. **LLM 기반 2차 판단**

   * 애매한 경우에만 사용

---

## 6. 데이터베이스 설계

### 6.1 conversations

```sql
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT UNIQUE NOT NULL,
  title TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 messages

```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  role TEXT CHECK(role IN ('system','user','assistant','tool','search')),
  content TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata JSON,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

---

## 7. 시스템 흐름

### 7.1 일반 대화

```
User Input
 → Chat Manager (저장)
   → Context Assembler
     → LLM Service
       → 응답
 → DB 저장
```

### 7.2 검색 포함 대화

```
User Input
 → 검색 필요 판단
   → Search Service
     → 결과 정제
 → Context Assembler
 → LLM Service
 → 응답
 → DB 저장
```

---

## 8. 디렉토리 구조

```
src/
 ├── chat/
 │   ├── manager.py
 │   └── memory.py
 ├── prompt/
 │   ├── builder.py
 │   └── templates/
 ├── llm/
 │   └── providers/
 ├── search/
 └── database/
```

---

## 9. 구현 단계 (권장)

### Phase 1

* Ollama 연동
* CLI 기반 대화

### Phase 2

* DB 저장
* Short-term Memory

### Phase 3

* 검색 서비스 통합
* Context Assembler 완성

### Phase 4

* Vector DB
* Long-term Memory 요약

---

## 10. 요약

* LLM은 기억하지 않는다
* 기억은 시스템이 설계한다
* 검색은 시스템이 수행한다
* Context Assembler가 전체 품질을 결정한다

> 이 시스템의 품질은 **모델 크기보다 설계 품질**에 의해 결정된다.
