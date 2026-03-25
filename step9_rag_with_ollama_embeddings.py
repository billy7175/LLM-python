"""
Step 9: RAG 데모 (Ollama Embeddings + 로컬 문서 검색 + 답변 생성)

구성:
1) 로컬 문서를 청킹
2) Ollama embeddings API로 임베딩 생성
3) 코사인 유사도로 top-k 검색
4) 검색된 컨텍스트를 LLM(ollama_provider)에 주입해 답변

전제:
- Ollama 서버 실행: ollama serve
- 생성 모델(기본): llama3
- 임베딩 모델(기본): nomic-embed-text
  (필요 시: ollama pull nomic-embed-text)
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple

import requests
from dotenv import load_dotenv

from src.llm.ollama_provider import OllamaProvider


@dataclass
class DocumentChunk:
    source: str
    chunk_id: int
    text: str
    embedding: Optional[List[float]]


class SimpleOllamaRAG:
    """벡터 DB 없이 동작하는 간단한 RAG 검색기."""

    def __init__(
        self,
        base_url: str,
        embedding_model: str,
        chunk_size: int = 700,
        overlap: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[DocumentChunk] = []
        self.embedding_enabled = True

    def _embed(self, text: str) -> List[float]:
        # Ollama 버전에 따라 임베딩 엔드포인트가 다를 수 있어 순차적으로 시도한다.
        candidates = [
            ("/api/embed", {"model": self.embedding_model, "input": text}),
            ("/api/embeddings", {"model": self.embedding_model, "prompt": text}),
        ]
        last_error: Exception | None = None

        for path, payload in candidates:
            try:
                resp = requests.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    timeout=60,
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()

                # /api/embed: {"embeddings": [[...]]} 또는 {"embeddings": [...]}
                if "embeddings" in data:
                    embs = data["embeddings"]
                    if isinstance(embs, list) and embs and isinstance(embs[0], list):
                        return embs[0]
                    if isinstance(embs, list) and embs:
                        return embs

                # /api/embeddings: {"embedding": [...]}
                if "embedding" in data and data["embedding"]:
                    return data["embedding"]
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise ValueError(f"임베딩 API 호출 실패: {last_error}") from last_error
        raise ValueError("임베딩 API 경로를 찾지 못했습니다. Ollama 버전을 확인하세요.")

    def _split_text(self, text: str) -> List[str]:
        clean = " ".join(text.split())
        if not clean:
            return []

        chunks: List[str] = []
        step = max(1, self.chunk_size - self.overlap)
        start = 0
        while start < len(clean):
            end = start + self.chunk_size
            chunks.append(clean[start:end])
            start += step
        return chunks

    def build_index(self, files: Sequence[Path]) -> None:
        self.chunks.clear()
        embedding_failed = False
        for file_path in files:
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding="utf-8")
            pieces = self._split_text(text)
            for i, piece in enumerate(pieces):
                emb: Optional[List[float]] = None
                if not embedding_failed:
                    try:
                        emb = self._embed(piece)
                    except Exception:
                        embedding_failed = True
                        self.embedding_enabled = False
                self.chunks.append(
                    DocumentChunk(
                        source=file_path.name,
                        chunk_id=i,
                        text=piece,
                        embedding=emb,
                    )
                )

        if not self.chunks:
            raise ValueError("인덱싱된 문서 청크가 없습니다. 파일 경로를 확인하세요.")

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {tok for tok in cleaned.split() if len(tok) >= 2}

    def _retrieve_keyword(
        self,
        query: str,
        top_k: int = 4,
        allowed_sources: Optional[Set[str]] = None,
    ) -> List[DocumentChunk]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scored = []
        for chunk in self.chunks:
            if allowed_sources is not None and chunk.source not in allowed_sources:
                continue
            c_tokens = self._tokenize(chunk.text)
            overlap = len(q_tokens & c_tokens)
            scored.append((overlap, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = [chunk for score, chunk in scored if score > 0][:top_k]
        return best

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        allowed_sources: Optional[Set[str]] = None,
    ) -> List[DocumentChunk]:
        if self.embedding_enabled:
            try:
                q_emb = self._embed(query)
                scored = []
                for chunk in self.chunks:
                    if allowed_sources is not None and chunk.source not in allowed_sources:
                        continue
                    if chunk.embedding is None:
                        continue
                    score = self._cosine_similarity(q_emb, chunk.embedding)
                    scored.append((score, chunk))
                if scored:
                    scored.sort(key=lambda x: x[0], reverse=True)
                    # 점수가 너무 낮으면 무관 컨텍스트 주입을 피한다.
                    if scored[0][0] < 0.20:
                        return []
                    return [chunk for _, chunk in scored[:top_k]]
            except Exception:
                self.embedding_enabled = False

        return self._retrieve_keyword(query, top_k=top_k, allowed_sources=allowed_sources)


def _should_use_rag(user_input: str) -> Tuple[bool, str]:
    """현업식 간단 라우터: 잡담은 RAG 스킵, 문서/프로젝트 질문만 RAG 사용."""
    text = user_input.strip()
    lowered = text.lower()

    if not text:
        return False, "empty"

    greeting_patterns = [
        r"^(hi|hello|hey|yo|sup)\b",
        r"^(안녕|하이|ㅎㅇ|반가워)",
        r"^(good morning|good afternoon|good evening)",
    ]
    if any(re.search(pat, lowered) for pat in greeting_patterns):
        return False, "smalltalk_greeting"

    smalltalk_words = {"고마워", "thanks", "thank you", "땡큐", "bye", "잘가", "굿나잇"}
    if lowered in smalltalk_words or len(text) <= 4:
        return False, "smalltalk_short"

    rag_keywords = {
        "step",
        "readme",
        "design",
        "progress",
        "프로젝트",
        "문서",
        "코드",
        "구현",
        "설계",
        "rag",
        "db",
        "postgres",
        "sqlite",
        "context",
        "assembler",
        "memory",
        "chatmanager",
        "파일",
        "목록",
        "리스트",
        "인덱싱",
        "스캔",
        "scan",
        "files",
    }
    if any(k in lowered for k in rag_keywords):
        return True, "project_keyword"

    question_signals = {"?", "왜", "어떻게", "무엇", "뭐", "차이", "설명", "정리"}
    if any(sig in text for sig in question_signals):
        # 일반 질문은 우선 비RAG로 처리하여 오검출을 줄인다.
        return False, "generic_question"

    return False, "default_chat"


def _is_followup_for_rag(user_input: str) -> bool:
    """직전 문서 질의를 이어받는 후속 질문인지 간단히 판별."""
    text = user_input.strip().lower()
    followup_signals = [
        "안에",
        "내용",
        "자세히",
        "더",
        "그거",
        "그건",
        "그 문서",
        "그 파일",
        "요약",
        "설명해줘",
        "무슨 말",
    ]
    return any(sig in text for sig in followup_signals)


def _discover_knowledge_files(root: Path) -> List[Path]:
    """프로젝트 문서를 자동 탐색한다."""
    include_exts = {".md", ".txt"}
    exclude_dirs = {".git", "venv", "__pycache__", ".idea", ".vscode", "node_modules"}
    max_size_bytes = 400_000  # 너무 큰 파일은 인덱싱 제외

    found: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue

        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.suffix.lower() not in include_exts:
            continue

        try:
            if p.stat().st_size > max_size_bytes:
                continue
        except OSError:
            continue

        found.append(p)

    found.sort(key=lambda x: str(x))
    return found


def _extract_explicit_filenames(user_input: str) -> Set[str]:
    """사용자 입력에 명시된 파일명(.md/.txt)을 추출한다. (예: DESIGN.md)"""
    matches = re.findall(r"([A-Za-z0-9_.-]+\.(?:md|txt))", user_input, flags=re.IGNORECASE)
    return {m for m in matches}


def _is_about_the_file_itself(user_input: str) -> bool:
    """'DESIGN.md 알려줘/뭐야/요약/내용'처럼 파일 자체 설명/요약 요청인지 판별."""
    lowered = user_input.strip().lower()
    signals = ["뭐야", "무슨", "무엇", "알려줘", "요약", "내용", "정리", "설명"]
    return any(sig in lowered for sig in signals)


def _take_first_chunks_for_sources(
    chunks: List[DocumentChunk],
    sources: Set[str],
    top_k: int,
) -> List[DocumentChunk]:
    """특정 source에 대해 앞쪽 청크부터 top_k를 가져온다."""
    picked: List[DocumentChunk] = []
    source_lower = {s.lower() for s in sources}
    for ch in sorted(chunks, key=lambda c: (c.source, c.chunk_id)):
        if ch.source.lower() not in source_lower:
            continue
        picked.append(ch)
        if len(picked) >= top_k:
            break
    return picked


def main() -> None:
    load_dotenv()

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    generation_model = os.getenv("OLLAMA_MODEL", "llama3")
    embedding_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    print("=" * 68)
    print("Step9 RAG 챗 (Ollama Embeddings 기반)")
    print("종료하려면 'quit' 또는 'exit' 입력")
    print("=" * 68)
    print(
        f"[설정] generation_model={generation_model}, embedding_model={embedding_model}"
    )

    rag = SimpleOllamaRAG(
        base_url=base_url,
        embedding_model=embedding_model,
        chunk_size=700,
        overlap=120,
    )

    # 프로젝트 문서를 자동 탐색하여 지식 소스로 사용
    project_root = Path(".").resolve()
    knowledge_files = _discover_knowledge_files(project_root)

    try:
        print("\n[준비] 문서 인덱싱 중... (최초 1회, 다소 느릴 수 있음)")
        rag.build_index(knowledge_files)
        rel_names = [str(p.relative_to(project_root)) for p in knowledge_files]
        print(f"[준비] 인덱싱 문서 수: {len(knowledge_files)}")
        print(f"[준비] 문서 목록: {', '.join(rel_names[:8])}")
        if len(rel_names) > 8:
            print(f"[준비] ... 외 {len(rel_names) - 8}개")
        print(f"[준비] 완료! 총 청크 수: {len(rag.chunks)}")
        if rag.embedding_enabled:
            print("[검색모드] embedding 검색")
        else:
            print("[검색모드] keyword fallback (임베딩 API 미지원 환경)")
    except Exception as e:
        print(f"\n❌ 인덱싱 실패: {e}")
        print("💡 확인:")
        print("   - ollama serve 실행 여부")
        print("   - ollama pull nomic-embed-text (선택)")
        print("   - 프로젝트에 .md/.txt 문서가 존재하는지")
        return

    llm = OllamaProvider(model=generation_model)

    system_prompt = """당신은 프로젝트 분석 도우미입니다.
아래 RAG 컨텍스트를 최우선 근거로 답변하세요.
- 근거가 부족하면 모른다고 말하세요.
- **반드시 한국어로만** 답변하세요. (영어/혼용 금지)
- 가능한 한 간결하고 정확하게 답변하세요.
- 답변 마지막에 참고한 source 파일명을 짧게 덧붙이세요."""
    last_mode = "init"
    last_explicit_sources: Set[str] = set()

    while True:
        user_input = input("\n[당신]: ").strip()
        if user_input.lower() in {"quit", "exit", "q", "종료"}:
            print("\n👋 종료합니다.")
            break
        if not user_input:
            continue

        try:
            # 운영성 명령: LLM을 거치지 않고 즉시 응답
            cmd = user_input.strip().lower()
            if cmd in {"files", "file", "문서목록", "파일목록", "목록", "list"} or (
                "접근" in user_input and "파일" in user_input
            ):
                rel_names = [str(p.relative_to(project_root)) for p in knowledge_files]
                print("\n[봇]: 제가 참고(인덱싱) 중인 문서 목록입니다.")
                for name in rel_names:
                    print(f"- {name}")
                print("[모드] system (indexed_files)")
                continue

            use_rag, route_reason = _should_use_rag(user_input)
            if (not use_rag) and last_mode.startswith("rag") and _is_followup_for_rag(user_input):
                use_rag, route_reason = True, "followup_after_rag"
            if not use_rag:
                messages = [
                    {
                        "role": "system",
                        "content": "당신은 친절한 어시스턴트입니다. **반드시 한국어로만** 간결하고 정확하게 답변하세요. (영어/혼용 금지)",
                    },
                    {"role": "user", "content": user_input},
                ]
                answer = llm.generate(messages, temperature=0.4)
                print("\n[봇]:", answer)
                print(f"[모드] chat ({route_reason})")
                last_mode = "chat"
                continue

            explicit = _extract_explicit_filenames(user_input)
            if explicit:
                last_explicit_sources = set(explicit)
            allowed_sources = last_explicit_sources or None

            # 파일명이 명시됐고 "그 파일 자체"를 물으면, 검색 스코어링 실패를 피하기 위해
            # 해당 파일의 앞부분 청크를 우선 컨텍스트로 제공한다.
            if explicit and _is_about_the_file_itself(user_input):
                top_chunks = _take_first_chunks_for_sources(
                    rag.chunks,
                    sources=explicit,
                    top_k=4,
                )
            else:
                top_chunks = rag.retrieve(
                    user_input,
                    top_k=4,
                    allowed_sources=allowed_sources,
                )
            if not top_chunks:
                messages = [
                    {
                        "role": "system",
                        "content": "당신은 프로젝트 분석 도우미입니다. 불확실하면 솔직히 모른다고 답하세요.",
                    },
                    {"role": "user", "content": user_input},
                ]
                answer = llm.generate(messages, temperature=0.3)
                print("\n[봇]:", answer)
                print("[모드] rag (no_relevant_context)")
                last_mode = "rag_no_context"
                continue

            context_blocks = []
            used_sources = []
            for ch in top_chunks:
                context_blocks.append(f"[source={ch.source}#{ch.chunk_id}] {ch.text}")
                used_sources.append(ch.source)

            rag_context = "\n\n".join(context_blocks)
            user_prompt = (
                f"질문: {user_input}\n\n"
                f"RAG_CONTEXT:\n{rag_context}\n\n"
                "위 컨텍스트만 근거로 답변하세요."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            answer = llm.generate(messages, temperature=0.2)
            print("\n[봇]:", answer)
            print("[모드] rag")
            print(f"[참고소스] {', '.join(sorted(set(used_sources)))}")
            last_mode = "rag"

        except Exception as e:
            print(f"\n❌ 처리 중 오류: {e}")


if __name__ == "__main__":
    main()

