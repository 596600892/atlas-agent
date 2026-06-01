#!/usr/bin/env python3
"""
Atlas CLI — 命令行入口
=======================
Complete command-line interface for Atlas.
Atlas 的完整命令行界面。

Usage / 使用方法:
    atlas              — Interactive text mode / 交互文本模式
    atlas --voice      — Interactive voice mode / 交互语音模式
    atlas ask <query>  — One-shot query / 单次查询
    atlas info         — Show system info / 显示系统信息
    atlas agents       — List registered agents / 列出已注册Agent
    atlas memory search <query>   Search memory / 搜索记忆
    atlas memory semantic <query> Semantic search / 语义搜索
    atlas memory graph <id>       Show memory graph / 记忆图谱
    atlas memory consolidate      Merge similar memories / 合并相似记忆
    atlas check                    Verify modules / 检查模块
"""

import argparse
import logging
import os
import sys
import shlex

from atlas_core.architecture import ATLAS_MODULES, verify_integrity
from atlas_core.router_engine import (
    AgentCapability,
    IntentRouter,
    REGISTRY,
    create_router,
)

# ---------------------------------------------------------------------------
# 日志配置 / Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("atlas.cli")


# ---------------------------------------------------------------------------
# 命令处理函数 / Command handlers
# ---------------------------------------------------------------------------

def cmd_interactive(args: argparse.Namespace):
    """启动交互模式 / Start interactive mode (default)"""
    from atlas_core.core import Atlas

    voice_mode = getattr(args, "voice", False)
    atlas = Atlas(
        voice_enabled=voice_mode,
        memory_enabled=True,
        data_dir="~/.atlas",
    )
    atlas.run(voice_mode=voice_mode)


def cmd_ask(args: argparse.Namespace):
    """单次查询 / One-shot query"""
    from atlas_core.core import Atlas

    query = args.query
    if not query:
        print("Error: No query provided / 错误：未提供查询")
        sys.exit(1)

    atlas = Atlas(
        voice_enabled=False,
        memory_enabled=True,
        data_dir="~/.atlas",
    )
    result = atlas.process(query)

    print(result["response"])

    # 如果有记忆上下文，显示 / Show memory context if available
    if result.get("memory_context"):
        print(f"\n[Memory / 记忆: {result['memories_recalled']} items recalled]")

    # 显示路由信息 / Show routing info
    if result["intent"] != "unknown" and result["intent"] != "error":
        print(
            f"\n[Intent / 意图: {result['intent']} | "
            f"Confidence / 置信度: {result['confidence']:.1%}]"
        )
        if result["matched_agents"]:
            agents_str = ", ".join(
                f"{name} ({conf:.1%})" for name, conf in result["matched_agents"]
            )
            print(f"[Agents / Agent: {agents_str}]")


def cmd_info(args: argparse.Namespace):
    """显示系统信息 / Show system information"""
    from atlas_core.core import Atlas

    atlas = Atlas(voice_enabled=False, memory_enabled=False)
    info = atlas.get_info()

    print(f"\n{'='*50}")
    print(f"  Atlas Agent v{info['version']}")
    print(f"  {info['agents_registered']} agents registered")
    print(f"{'='*50}")
    print()

    # 架构模块信息 / Architecture module info
    print(f"Architecture Modules / 架构模块 ({len(ATLAS_MODULES)}):")
    print("-" * 50)
    for name, mod in ATLAS_MODULES.items():
        caps = ", ".join(c.value for c in mod["contributes"])
        print(f"  [{name}]")
        print(f"    Lead: {mod['lead_agent']}")
        print(f"    Desc: {mod['description']}")
        print(f"    Caps: {caps}")
        print()

    # 运行时状态 / Runtime status
    print(f"Runtime Status / 运行时状态:")
    print(f"  Data dir / 数据目录: {info['data_dir']}")
    print(f"  Voice engine / 语音引擎: {'ON' if info['voice_enabled'] else 'OFF'}")
    print(f"  Memory engine / 记忆引擎: {'ON' if info['memory_enabled'] else 'OFF'}")
    print(f"  Queries processed / 已处理查询: {info['queries_processed']}")
    print(f"  Session duration / 会话时长: {info['session_duration_seconds']}s")
    print()


def cmd_agents(args: argparse.Namespace):
    """列出所有注册的 Agent / List all registered agents"""
    router = create_router()
    all_agents = router.list_all()

    print(f"\n{'='*60}")
    print(f"  Registered Agents / 已注册 Agent ({len(all_agents)})")
    print(f"{'='*60}")
    print()

    for agent in all_agents:
        caps = ", ".join(c.value for c in agent.capabilities)
        print(f"  [{agent.name}]")
        print(f"    Capabilities / 能力: {caps}")
        print(f"    Description / 描述: {agent.description}")
        print(f"    Repo / 仓库: {agent.repo_url}")
        print(f"    Package / 包: {agent.pip_package or '(not available / 不可用)'}")
        print()

    # 按能力分组显示 / Group by capability
    print(f"{'='*60}")
    print(f"  By Capability / 按能力分类")
    print(f"{'='*60}")
    for cap in AgentCapability:
        agents = router.list_by_capability(cap)
        names = ", ".join(a.name for a in agents)
        print(f"  {cap.value:25s} → {names}")
    print()


def cmd_memory(args: argparse.Namespace):
    """记忆操作 / Memory operations"""
    from atlas_core.memory_engine import create_memory_engine

    db_path = os.path.expanduser("~/.atlas/memory.db")
    engine = create_memory_engine(db_path)

    subcommand = args.memory_command
    if subcommand == "search":
        query = args.query
        if not query:
            print("Error: No search query / 错误：未提供搜索关键词")
            sys.exit(1)

        query_text = " ".join(query) if isinstance(query, list) else query
        results = engine.store.recall(query_text, limit=10)
        if not results:
            print(f"No memories found for: {query_text}")
            print(f"未找到相关记忆：{query_text}")
        else:
            print(f"\nMemory search results for / 记忆搜索结果: '{query_text}'")
            print("=" * 60)
            for i, m in enumerate(results, 1):
                print(f"\n  [{i}] Key / 键: {m.get('key', 'N/A')}")
                print(f"      Type / 类型: {m.get('type', 'N/A')}")
                print(f"      Content / 内容: {m.get('content', 'N/A')[:150]}")
                print(f"      Importance / 重要性: {m.get('importance', 0):.2f}")
                tags = m.get("tags", [])
                if tags:
                    print(f"      Tags / 标签: {', '.join(tags)}")
                related = m.get("related_ids", [])
                if related:
                    print(f"      Related / 关联: {related}")

    elif subcommand == "semantic":
        query = args.query
        if not query:
            print("Error: No search query / 错误：未提供搜索文本")
            sys.exit(1)

        query_text = " ".join(query) if isinstance(query, list) else query
        results = engine.vector_search.search(query_text, limit=10)
        if not results:
            print(f"No semantic results for: {query_text}")
            print(f"(sentence-transformers not installed or no embeddings stored)")
        else:
            print(f"\nSemantic search / 语义搜索: '{query_text}'")
            print("=" * 60)
            for i, (mid, score) in enumerate(results, 1):
                mem = engine.store.get_by_id(mid)
                if mem:
                    print(f"\n  [{i}] ID: {mid} (similarity: {score:.2%})")
                    print(f"      Key / 键: {mem.get('key', 'N/A')}")
                    print(f"      Content / 内容: {mem.get('content', 'N/A')[:150]}")
                    print(f"      Importance / 重要性: {mem.get('importance', 0):.2f}")

    elif subcommand == "graph":
        mid = args.id
        graph = engine.store.get_memory_graph(mid, depth=2)
        if not graph:
            print(f"No memory found with ID: {mid}")
            print(f"未找到 ID 为 {mid} 的记忆")
        else:
            print(f"\nMemory graph for / 记忆图谱 ID: {mid}")
            print("=" * 60)
            for gid, node in graph.items():
                rel_ids = node.get("related", [])
                rel_str = ", ".join(str(r) for r in rel_ids) if rel_ids else "(none)"
                print(f"\n  [{gid}] {node.get('type', 'N/A')}")
                print(f"      Content / 内容: {node.get('content', 'N/A')[:100]}")
                print(f"      Importance / 重要性: {node.get('importance', 0):.2f}")
                print(f"      Related / 关联: {rel_str}")

    elif subcommand == "consolidate":
        print("Running memory consolidation / 开始合并记忆...")
        stats_before = engine.consolidator.get_stats()
        print(f"  Before / 合并前: {stats_before['total']} memories, "
              f"{stats_before['potential_duplicates']} potential duplicates")

        result = engine.consolidator.consolidate(similarity_threshold=0.85)
        print(f"  Merged / 合并: {result['merged_count']}, "
              f"Deleted / 删除: {result['deleted_count']}")

        stats_after = engine.consolidator.get_stats()
        print(f"  After / 合并后: {stats_after['total']} memories")

        print("\nDone / 完成 ✓")

    else:
        print(f"Unknown memory command: {subcommand}")
        print("Usage / 使用方法:")
        print("  atlas memory search <query>")
        print("  atlas memory semantic <query>")
        print("  atlas memory graph <id>")
        print("  atlas memory consolidate")
        sys.exit(1)


def cmd_check(args: argparse.Namespace):
    """完整性检查 / Integrity check of all modules"""
    from atlas_core.core import Atlas

    errors = []

    # 1. 架构完整性 / Architecture integrity
    print("Checking architecture / 检查架构完整性...", end=" ")
    arch_errors = verify_integrity()
    if arch_errors:
        errors.extend(f"[Architecture] {e}" for e in arch_errors)
        print("FAILED")
    else:
        print("PASSED ✓")

    # 2. 路由引擎 / Router engine
    print("Checking router engine / 检查路由引擎...", end=" ")
    try:
        router = create_router()
        if router.registry_size == 14:
            print(f"PASSED ✓ ({router.registry_size} agents)")
        else:
            errors.append(f"[Router] Expected 14 agents, got {router.registry_size}")
            print("FAILED")
    except Exception as e:
        errors.append(f"[Router] {e}")
        print(f"FAILED ({e})")

    # 3. Atlas 核心 / Atlas core
    print("Checking Atlas core / 检查 Atlas 核心...", end=" ")
    try:
        atlas = Atlas(voice_enabled=False, memory_enabled=True)
        core_errors = atlas.check()
        for e in core_errors:
            errors.append(f"[Core] {e}")
        if core_errors:
            print("WARNINGS")
            for e in core_errors:
                print(f"  - {e}")
        else:
            print("PASSED ✓")
    except Exception as e:
        errors.append(f"[Core] {e}")
        print(f"FAILED ({e})")

    # 4. 语音引擎 / Voice engine
    print("Checking voice engine / 检查语音引擎...", end=" ")
    try:
        from atlas_core.voice_engine import SpeechToText, TextToSpeech
        print("PASSED ✓ (import ok)")
    except ImportError:
        print("SKIPPED (dependencies not installed)")
    except Exception as e:
        print(f"WARNING ({e})")

    # 5. 记忆引擎 / Memory engine
    print("Checking memory engine / 检查记忆引擎...", end=" ")
    try:
        from atlas_core.memory_engine import MemoryStore
        print("PASSED ✓ (import ok)")
    except Exception as e:
        print(f"FAILED ({e})")

    # 汇总 / Summary
    print()
    print("=" * 50)
    if errors:
        print(f"CHECK COMPLETED WITH {len(errors)} ERROR(S):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED ✓ / 所有检查通过 ✓")
        print("Atlas is ready to use! / Atlas 已就绪！")


# ---------------------------------------------------------------------------
# WebUI / Electron 命令
# ---------------------------------------------------------------------------


def cmd_web(args: argparse.Namespace):
    """启动 WebUI 服务器 / Start WebUI server"""
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8640)
    debug = getattr(args, "debug", False)

    try:
        from atlas_core.webui import run_server

        run_server(host=host, port=port, debug=debug)
    except ImportError as e:
        print(
            "Error: Flask is required for WebUI.\n"
            "Install with: pip install atlas-agent[webui]  or  pip install flask"
        )
        sys.exit(1)


def cmd_electron(args: argparse.Namespace):
    """启动 Electron 桌面应用 / Launch Electron desktop app"""
    import shutil
    import subprocess

    electron_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "webui",
        "electron",
    )

    if not os.path.exists(os.path.join(electron_dir, "node_modules")):
        print("Electron dependencies not found. Installing...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=electron_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"npm install failed:\n{result.stderr}")
            sys.exit(1)

    # 先启动 WebUI 后端
    print("Starting Atlas WebUI backend...")
    from atlas_core.webui import create_app

    app = create_app()

    import threading

    def _run():
        app.run(host="127.0.0.1", port=8640, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    import time

    time.sleep(1)

    # 启动 Electron
    print("Launching Electron desktop app...")
    electron_bin = shutil.which("electron")
    if electron_bin:
        subprocess.run([electron_bin, electron_dir])
    else:
        print(
            "Electron not found on PATH. Try:\n"
            "  cd webui/electron && npx electron ."
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# 主入口 / Main entry point
# ---------------------------------------------------------------------------

def main():
    """CLI 主入口 / CLI main entry point"""
    parser = argparse.ArgumentParser(
        description="Atlas — 通用人工智能体 / Universal AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / 示例:
    atlas                          Interactive chat / 交互对话
    atlas --voice                  Voice mode / 语音模式
    atlas ask "what is AAPL stock" One-shot query / 单次查询
    atlas info                     System info / 系统信息
    atlas agents                   List agents / 列出Agent
    atlas memory search <query>   Search memory / 搜索记忆
    atlas memory semantic <query> Semantic search / 语义搜索
    atlas memory graph <id>       Show memory graph / 记忆图谱
    atlas memory consolidate      Merge similar memories / 合并相似记忆
    atlas check                    Verify modules / 检查模块
        """,
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice mode / 启用语音模式",
    )

    sub = parser.add_subparsers(dest="command")

    # ask <query>
    ask_parser = sub.add_parser("ask", help="Ask a question / 提问")
    ask_parser.add_argument("query", nargs="*", help="Your question / 你的问题")

    # info
    sub.add_parser("info", help="Show system info / 显示系统信息")

    # agents
    sub.add_parser("agents", help="List registered agents / 列出已注册Agent")

    # memory search <query>
    mem_parser = sub.add_parser("memory", help="Memory operations / 记忆操作")
    mem_sub = mem_parser.add_subparsers(dest="memory_command")
    mem_search = mem_sub.add_parser("search", help="Search memory / 搜索记忆")
    mem_search.add_argument("query", nargs="*", help="Search keywords / 搜索关键词")
    mem_semantic = mem_sub.add_parser("semantic", help="Semantic search / 语义搜索")
    mem_semantic.add_argument("query", nargs="*", help="Search text / 搜索文本")
    mem_graph = mem_sub.add_parser("graph", help="Show memory graph / 记忆图谱")
    mem_graph.add_argument("id", type=int, help="Memory ID / 记忆 ID")
    mem_consolidate = mem_sub.add_parser("consolidate", help="Merge similar memories / 合并相似记忆")

    # web
    web_parser = sub.add_parser("web", help="Launch WebUI / 启动 Web 界面")
    web_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    web_parser.add_argument("--port", type=int, default=8640, help="Bind port")
    web_parser.add_argument("--debug", action="store_true", help="Debug mode")

    # electron
    sub.add_parser("electron", help="Launch Electron desktop app / 启动桌面应用")

    # check
    sub.add_parser("check", help="Verify all modules / 检查所有模块")

    # 解析参数 / Parse arguments
    args = parser.parse_args()

    # 处理命令 / Handle commands
    cmd = args.command

    if cmd is None:
        # 默认: 交互模式 / Default: interactive mode
        cmd_interactive(args)
    elif cmd == "ask":
        # 合并查询词 / Join query words
        args.query = " ".join(args.query) if args.query else ""
        cmd_ask(args)
    elif cmd == "info":
        cmd_info(args)
    elif cmd == "agents":
        cmd_agents(args)
    elif cmd == "memory":
        # 合并查询词 / Join query words for memory subcommand
        if hasattr(args, "query") and args.query:
            args.query = " ".join(args.query)
        cmd_memory(args)
    elif cmd == "check":
        cmd_check(args)
    elif cmd == "web":
        cmd_web(args)
    elif cmd == "electron":
        cmd_electron(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
