"""
Atlas Agent — 快速入门示例
Quickstart example

用法: python examples/quickstart.py
"""

from atlas_core.core import create_atlas


def main():
    # 1. 创建 Atlas 实例 (禁用语音和记忆以简化)
    atlas = create_atlas(voice_enabled=False, memory_enabled=False)

    # 2. 查看系统信息
    info = atlas.get_info()
    print(f"Atlas v{info['version']}")
    print(f"已注册 {info['agents_registered']} 个 Agent")
    print()

    # 3. 查询示例
    queries = [
        "今天市场怎么样？",
        "write a screenplay for a sci-fi movie",
        "generate an image of a sunset",
        "check system health",
    ]

    for q in queries:
        result = atlas.process(q)
        intent = result["intent"]
        confidence = result["confidence"]
        matched = [name for name, _ in result.get("matched_agents", [])]
        print(f"  用户: {q}")
        print(f"  意图: {intent} (置信度: {confidence:.1%})")
        print(f"  匹配: {matched}")
        print(f"  响应: {result['response'][:80]}...")
        print()


if __name__ == "__main__":
    main()
