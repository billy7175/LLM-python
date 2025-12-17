# 로컬 LLM 챗 시스템

로컬 LLM(Ollama)을 사용하여 대화 기록을 기억하고 인터넷 검색 기능을 제공하는 챗 시스템입니다.

## 요구사항

- Python 3.9+
- Ollama 설치 및 실행 중

## 설치

1. 저장소 클론:
```bash
git clone <repository-url>
cd llm-project
```

2. 가상환경 생성 및 활성화:
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

3. 패키지 설치:
```bash
pip install -r requirements.txt
```

4. 데이터베이스 초기화:
```bash
python init_db.py
```

5. Ollama 설치 및 모델 다운로드:
```bash
# Ollama 설치 (macOS)
brew install ollama

# 모델 다운로드
ollama pull llama3

# Ollama 서버 실행 (별도 터미널에서)
ollama serve
```

## 사용법

### 1. Ollama 서버 실행 (필수)

**별도 터미널에서 Ollama 서버를 먼저 실행해야 합니다:**

```bash
ollama serve
```

서버가 정상적으로 실행 중인지 확인:
```bash
curl http://localhost:11434/api/tags
```

### 2. 챗봇 실행

**가장 완성된 버전 (DB 저장 지원):**
```bash
# 가상환경 활성화 (설치 시 이미 했을 수도 있음)
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 챗봇 실행
python step5_chat_with_db_interactive.py
```

**사용 예시:**
```
[당신]: 안녕하세요
[봇]: 안녕하세요! 무엇을 도와드릴까요?

[당신]: 내 이름은 철수예요
[봇]: 안녕하세요 철수님! 반갑습니다.

[당신]: 내 이름이 뭐였지?
[봇]: 철수님이라고 하셨죠!

[당신]: quit  # 종료
```

**종료:** `quit`, `exit`, `q`, `종료` 중 하나 입력

### 3. 다른 단계 테스트 (선택사항)

개발 단계별 테스트:
```bash
# Ollama Provider 기본 테스트
python step0_test_ollama.py

# Context Assembler 테스트
python step2_test_context_assembler.py

# Chat Manager 테스트 (메모리만 사용, 프로그램 종료 시 초기화)
python step3_chat_manager_interactive.py

# DB 저장/로드 테스트
python step4_db_memory.py

# DB 통합 챗 (가장 완성된 버전)
python step5_chat_with_db_interactive.py
```

**주요 차이점:**
- `step3`: 메모리에만 저장 (프로그램 종료 시 초기화)
- `step5`: DB에 저장 (프로그램 재시작해도 대화 기록 유지)

## 프로젝트 구조

```
src/
├── llm/          # LLM 서비스 (Ollama Provider)
├── chat/         # 채팅 관리자
├── memory/       # 메모리 관리
├── search/       # 검색 서비스
├── prompt/       # 프롬프트 및 Context Assembler
└── database/     # 데이터베이스
```

## 구현 현황

자세한 구현 현황은 `PROGRESS.md`를 참조하세요.

## 참고 문서

- `DESIGN.md`: 시스템 설계 문서
- `steps.md`: 구현 로드맵
- `PROGRESS.md`: 구현 진행 상황

