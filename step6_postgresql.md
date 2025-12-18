# Step 6 — PostgreSQL 연결 (기존 방식 유지, DB명 동일)

목표:
- 기존 SQLite 기반 구현은 **그대로 유지**한다. (기존 `step*.py` 실행이 깨지면 안 됨)
- PostgreSQL은 **별도 단계(step6)에서만** “연결 방법/운영 방식”을 문서화한다.
- DB 이름은 기존 프로젝트와 동일하게 `nestjs_db`를 사용한다. (`POSTGRES_DB` 기본값)

---

## 1) 전제: 지금 레포는 기본이 SQLite다

현재 코드(`src/database/db.py`)는 기본적으로 SQLite(`data/chat.db`)에 연결되어 있습니다.

즉, **이 문서(step6)만 작성한다고 해서 기존 파이썬 코드가 자동으로 Postgres에 저장되지는 않습니다.**

PostgreSQL에 “실제로 저장”까지 하려면, step6에서 별도의 DB 연결 모듈/엔트리포인트를 추가하거나,
기존 DB 연결을 환경변수 기반으로 확장하는 작업이 필요합니다. (기존 SQLite 흐름은 유지)

---

## 2) PostgreSQL 컨테이너 구성 (기존 프로젝트 compose 그대로)

아래는 “이미 다른 프로젝트에서 사용 중”인 PostgreSQL 예시입니다.
DB 이름은 기본값 `nestjs_db`(= 동일 DB명)로 유지합니다.

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: nestjs-postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-nestjs_db}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### 핵심 포인트
- `POSTGRES_DB`의 기본값이 `nestjs_db`이므로, “DB명 동일” 요구사항을 만족합니다.
- `ports: 5432:5432` 형태면, **호스트(macOS)에서** `localhost:5432`로 접근 가능합니다.

---

## 3) 접속 정보(DATABASE_URL) 만들기

PostgreSQL 접속 정보는 보통 아래 한 줄로 표현합니다:

```text
postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
```

docker-compose의 기본값을 그대로 사용할 경우(호스트에서 Python 실행 기준):

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/nestjs_db
```

### 호스트/컨테이너 구분
- **호스트에서 실행(지금 로컬에서 python 실행)**: `HOST=localhost`, `PORT=5432`
- **다른 컨테이너에서 실행(예: app 컨테이너)**: `HOST=postgres`(서비스명), `PORT=5432`

---

## 4) “DB명 동일(nestjs_db)”로 쓸 때의 주의사항

### 같은 DB를 공유한다는 의미
`nestjs_db`를 그대로 쓰면, **다른 프로젝트와 같은 DB를 공유**할 수 있습니다.

이 경우 충돌/오염을 막으려면 아래 중 하나를 권장합니다:
- **(권장) 스키마 분리**: 같은 DB 안에 스키마를 나눠서 테이블 충돌 방지
- **또는 테이블 네이밍 전략/마이그레이션 규칙**을 엄격히 적용

> “테이블 이름만 바꾸기”는 코드/모델 수정이 필요하고 관리 난이도가 올라가므로,
> 보통은 **DB 분리(DBNAME 변경)** 또는 **스키마 분리**가 더 깔끔합니다.

---

## 5) (선택) 접근 확인 체크리스트

다음이 만족되면 Postgres 접근이 가능한 상태입니다:
- 컨테이너가 실행 중이다
- 5432 포트가 열려 있다(`POSTGRES_PORT`)
- 사용자/비밀번호/DB명이 맞다 (`postgres/postgres/nestjs_db` 등)

---

## 6) 다음 단계(구현)에서 할 일

이 step6 문서 다음으로 “정말로 Postgres에 저장”하려면, 아래 중 하나로 진행합니다.
(기존 SQLite 흐름은 그대로 유지)

- **옵션 A (권장, 안전)**: Postgres 전용 모듈/엔트리포인트를 새로 추가
  - 예: `src/database/db_postgres.py`, `step6_init_db_postgres.py`, `step6_chat_with_postgres.py`
- **옵션 B**: 기존 DB 연결을 `DATABASE_URL`로 스위치 가능하게 확장
  - 단, 기존 step 파일이 모두 같은 DB 연결을 공유하게 될 수 있으니 “기존 흐름 유지” 요구사항에 맞게 설계 필요

---

## 7) Step6 실행 파일 (PostgreSQL만 사용)

아래 파일들은 **step6에서만 PostgreSQL을 사용**합니다.
기존 SQLite 기반 파일들은 변경하지 않습니다.

### 7-1. PostgreSQL 테이블 생성

```bash
python step6_init_db_postgres.py
```

### 7-2. PostgreSQL 저장/로드 챗 실행

```bash
python step6_chat_with_postgres_interactive.py
```

### 환경변수 (둘 중 하나 방식)

- **방식 A: compose 환경변수 그대로**
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
  - 기본값은 `postgres/postgres/nestjs_db/localhost/5432`

- **방식 B: 한 줄 URL**
  - `STEP6_POSTGRES_DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/nestjs_db"`

> 참고: PostgreSQL 드라이버가 필요합니다. (`psycopg2-binary`)
> requirements.txt에서 주석 해제 후 설치하거나 별도로 설치해야 합니다.

---

## Appendix A) docker-compose 메모 (원문 보존)

아래는 위 “PostgreSQL 컨테이너 구성” 섹션에서 사용한 내용을 **참고용으로 그대로 보관**한 것입니다.

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: nestjs-postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-nestjs_db}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```


