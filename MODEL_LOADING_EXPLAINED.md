# 모델 로딩 방식 설명

## 핵심 차이: "직접 로드" vs "API 호출"

### 방법 1: Ollama 사용 (현재 steps.md 방식)

**설명:**
- Ollama가 모델을 로드하고 실행
- 우리 코드는 **HTTP 요청만 보냄**
- 모델 파일, GPU 메모리 관리 등을 Ollama가 처리

**구조:**
```
[우리 코드 (Node.js/Python)]
  ↓ HTTP 요청 (단순!)
  ↓
[Ollama 서버] ← 여기서 모델을 로드하고 실행
  ↓
[모델 파일 (.gguf 등)]
```

**코드 예시 (Node.js):**
```typescript
// 우리가 하는 일: HTTP 요청만!
const response = await fetch('http://localhost:11434/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    model: 'llama3',
    messages: [{ role: 'user', content: 'Hello' }]
  })
});

// Ollama가 알아서:
// 1. llama3 모델을 메모리에 로드
// 2. GPU 할당
// 3. 추론 실행
// 4. 결과 반환
```

**장점:**
- ✅ 간단함 (HTTP 요청만)
- ✅ 어떤 언어에서든 가능
- ✅ 모델 관리가 쉬움 (ollama pull/push)
- ✅ 메모리 관리를 Ollama가 함

**단점:**
- ⚠️ Ollama 서버가 실행 중이어야 함
- ⚠️ Ollama에 종속됨

---

### 방법 2: 직접 모델 로드 (Python transformers)

**설명:**
- 우리 코드에서 직접 모델 파일을 읽어서 메모리에 로드
- Python transformers 라이브러리 사용
- 추론도 우리 코드에서 직접 실행

**구조:**
```
[우리 Python 코드]
  ↓
[transformers 라이브러리]
  ↓
[모델 파일 (.safetensors, .bin 등) 직접 읽기]
  ↓
[GPU/CPU 메모리에 모델 로드]
  ↓
[우리 코드에서 직접 추론 실행]
```

**코드 예시 (Python):**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 1. 모델 파일을 직접 다운로드/로드
model_name = "meta-llama/Llama-3.2-3B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,  # GPU 메모리 관리
    device_map="auto"  # GPU 할당
)

# 2. 우리 코드에서 직접 추론
inputs = tokenizer("Hello", return_tensors="pt")
outputs = model.generate(**inputs, max_length=100)
response = tokenizer.decode(outputs[0])
```

**우리가 직접 해야 하는 일:**
1. ✅ 모델 파일 다운로드
2. ✅ GPU 메모리 할당
3. ✅ 모델을 메모리에 로드 (수 GB ~ 수십 GB)
4. ✅ 토큰화/디토큰화
5. ✅ 추론 실행
6. ✅ 메모리 관리

**장점:**
- ✅ 완전한 제어권
- ✅ Ollama 없이도 동작
- ✅ 커스텀 파인튜닝 모델 사용 가능
- ✅ 모델 구조 수정 가능

**단점:**
- ⚠️ 복잡함 (많은 코드 필요)
- ⚠️ GPU 메모리 직접 관리 필요
- ⚠️ Python에 강하게 종속됨
- ⚠️ 초기 로딩 시간이 김 (수초~수분)

---

## 비유로 이해하기

### Ollama 사용 = 택시 타기
```
우리: "강남역 가주세요"
  ↓
택시 기사(Ollama): 
  - 차량 준비 (모델 로드)
  - 길 안내 (추론 실행)
  - 목적지 도착 (결과 반환)
```

### 직접 로드 = 자가용 운전
```
우리:
  - 차량 구매 (모델 다운로드)
  - 차량 유지보수 (메모리 관리)
  - 운전 (추론 실행)
  - 주차 (메모리 해제)
```

---

## 이 프로젝트에서의 선택

### steps.md (Ollama 사용)

```typescript
// 이것만 하면 됨!
const response = await fetch('http://localhost:11434/api/chat', {
  method: 'POST',
  body: JSON.stringify({ model: 'llama3', messages: [...] })
});
```

**이유:**
- ✅ 간단하고 빠른 시작
- ✅ 모델 관리를 Ollama에 위임
- ✅ Node.js에서도 쉽게 사용 가능

### 만약 직접 로드한다면?

```python
# 이렇게 복잡해짐
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 모델 로드 (수 분 소요, 수 GB 메모리 사용)
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B")

# 추론
inputs = tokenizer("Hello", return_tensors="pt")
outputs = model.generate(**inputs)
```

**언제 직접 로드를 선택해야 하나?**
- 모델을 수정해야 할 때 (파인튜닝 등)
- Ollama가 지원하지 않는 모델을 사용할 때
- 더 세밀한 제어가 필요할 때

---

## 요약

| 구분 | Ollama 사용 | 직접 로드 |
|------|------------|----------|
| **모델 로드 위치** | Ollama 서버 | 우리 코드 |
| **코드 복잡도** | 낮음 (HTTP만) | 높음 (전체 파이프라인) |
| **언어 제약** | 없음 | Python 거의 필수 |
| **메모리 관리** | Ollama가 처리 | 우리가 직접 관리 |
| **제어권** | 낮음 | 높음 |
| **시작 속도** | 빠름 | 느림 (모델 로드 시간) |

**결론:** 
- 이 프로젝트는 **Ollama 사용**이 적합합니다
- "직접 로드"는 특별한 요구사항이 있을 때만 고려하면 됩니다
