# 기술 스택 선택 가이드

## 핵심 개념: Ollama는 언어 독립적

Ollama는 **독립적인 HTTP 서버**이므로, 어떤 언어에서든 호출 가능합니다.

```
Ollama 서버 (Go로 작성, 독립 실행)
  ↓
HTTP API (http://localhost:11434/api/chat)
  ↓
[Node.js | Python | Go | Rust | Java | ...]
```

## Python vs Node.js 비교

### Python 선택 시

**장점:**
- ✅ LLM 생태계가 가장 성숙함
- ✅ Hugging Face transformers로 직접 모델 로드 가능
- ✅ LangChain, LlamaIndex 등 강력한 프레임워크
- ✅ 벡터 DB 통합이 쉬움 (Chroma, FAISS)
- ✅ ML/AI 라이브러리가 풍부

**단점:**
- ⚠️ 비동기 처리가 복잡할 수 있음 (FastAPI 사용 권장)
- ⚠️ 웹 프론트엔드와 연동 시 별도 고려 필요

**Ollama 호출 예시:**
```python
import requests

response = requests.post(
    'http://localhost:11434/api/chat',
    json={
        'model': 'llama3',
        'messages': [
            {'role': 'user', 'content': 'Hello'}
        ]
    }
)
```

**추천 프레임워크:**
- FastAPI (API 서버)
- SQLAlchemy (ORM)
- Pydantic (타입 검증)

---

### Node.js 선택 시

**장점:**
- ✅ 웹 백엔드와 자연스러운 통합
- ✅ 비동기 처리가 간단함 (async/await)
- ✅ TypeScript로 타입 안정성 확보
- ✅ NestJS/Express 생태계 활용

**단점:**
- ⚠️ LLM 관련 라이브러리가 Python보다 적음
- ⚠️ 직접 모델 로드를 하려면 Python 래퍼 필요
- ⚠️ Ollama 의존도가 높아짐 (Ollama 없으면 동작 불가)

**Ollama 호출 예시:**
```typescript
const response = await fetch('http://localhost:11434/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'llama3',
    messages: [{ role: 'user', content: 'Hello' }]
  })
});
```

**추천 프레임워크:**
- NestJS 또는 Express (API 서버)
- Prisma 또는 TypeORM (ORM)
- TypeScript

---

## 현재 문서 상태

### steps.md
- **기술 스택**: Node.js (NestJS/Express)
- **이유**: 실전 구현 로드맵, 웹 백엔드 중심

### DESIGN.md
- **기술 스택**: Python (FastAPI)
- **이유**: LLM 생태계 중심 설계

---

## 권장 사항

### 프로젝트 목적에 따라 선택

**Python 추천 시나리오:**
- 벡터 DB 활용 계획
- LangChain 같은 프레임워크 활용
- 복잡한 RAG 시스템 구축
- 직접 모델 파인튜닝 계획

**Node.js 추천 시나리오:**
- 웹 애플리케이션 중심
- 기존 Node.js 스택과 통합
- 빠른 프로토타이핑
- Ollama만 사용할 계획

---

## 통합 접근 (하이브리드)

가장 강력한 방법은 **Python 백엔드 + Node.js 프론트엔드**:

```
[Node.js Frontend/API Gateway]
  ↓ HTTP
[Python Backend (LLM 처리, 벡터 DB)]
  ↓ HTTP
[Ollama Server]
```

하지만 단순성을 위해 **하나의 언어로 통일**하는 것을 권장합니다.

---

## 최종 권장사항

이 프로젝트의 요구사항을 고려하면:

1. **간단한 시작**: Node.js (steps.md 기준)
   - Ollama HTTP API 호출만 하면 됨
   - 빠른 프로토타이핑

2. **확장성 고려**: Python (DESIGN.md 기준)
   - 향후 벡터 DB, LangChain 등 활용 시 유리

**결론**: 두 언어 모두 가능하지만, **steps.md의 Node.js 기준으로 시작**하고, 필요시 Python으로 마이그레이션하는 것을 권장합니다.
