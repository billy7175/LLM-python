"""Context Assembler 테스트"""

from src.prompt.context_assembler import ContextAssembler, build_context


def test_basic_context():
    """기본 컨텍스트 조립 테스트"""
    print("=" * 60)
    print("Context Assembler 테스트")
    print("=" * 60)
    
    # Assembler 생성
    assembler = ContextAssembler(max_tokens=100)
    
    # 테스트 메모리
    memories = [
        {"role": "user", "content": "안녕하세요"},
        {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
        {"role": "user", "content": "내 이름은 철수입니다"},
        {"role": "assistant", "content": "반갑습니다 철수님!"}
    ]
    
    # 컨텍스트 조립
    context = assembler.build_context(
        memories=memories,
        user_message="내 이름이 뭐였지?"
    )
    
    print("\n✅ 조립된 컨텍스트:")
    print("-" * 60)
    for i, msg in enumerate(context, 1):
        role = msg["role"]
        content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
        print(f"{i}. [{role}]: {content}")
    
    print("-" * 60)
    print(f"\n총 메시지 수: {len(context)}")
    print(f"시스템 프롬프트 포함: {context[0]['role'] == 'system'}")
    print(f"사용자 메시지 포함: {context[-1]['role'] == 'user'}")


def test_token_limit():
    """토큰 제한 테스트"""
    print("\n" + "=" * 60)
    print("토큰 제한 테스트 (많은 메모리)")
    print("=" * 60)
    
    assembler = ContextAssembler(max_tokens=200)  # 작은 제한
    
    # 많은 메모리 생성
    memories = []
    for i in range(50):
        memories.append({
            "role": "user",
            "content": f"메시지 {i+1}: 이것은 테스트 메시지입니다. " * 3
        })
        memories.append({
            "role": "assistant",
            "content": f"응답 {i+1}: 네, 이해했습니다. " * 3
        })
    
    print(f"\n전체 메모리 수: {len(memories)}")
    
    # 컨텍스트 조립
    context = assembler.build_context(
        memories=memories,
        user_message="마지막 질문"
    )
    
    # 메모리에서 선택된 수 계산 (system + selected memories + user)
    selected_memories = len(context) - 2  # system과 user 제외
    
    print(f"선택된 메모리 수: {selected_memories}")
    print(f"최종 컨텍스트 메시지 수: {len(context)}")
    print(f"토큰 추정: {assembler._estimate_messages_tokens(context)}")


def test_convenience_function():
    """편의 함수 테스트"""
    print("\n" + "=" * 60)
    print("편의 함수 테스트")
    print("=" * 60)
    
    memories = [
        {"role": "user", "content": "안녕"},
        {"role": "assistant", "content": "안녕하세요!"}
    ]
    
    context = build_context(
        memories=memories,
        user_message="테스트"
    )
    
    print(f"✅ 편의 함수로 생성된 컨텍스트: {len(context)}개 메시지")


if __name__ == "__main__":
    test_basic_context()
    test_token_limit()
    test_convenience_function()
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)

