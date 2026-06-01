#!/usr/bin/env python3
"""
Atlas CLI — 命令行入口
"""

import argparse
import sys

from atlas_core.architecture import ATLAS_MODULES, verify_integrity


def cmd_info(args):
    """显示Atlas架构信息"""
    print(f"Atlas Agent v{args.get('version', '0.1.0')}")
    print(f"{'='*50}")
    print(f"Modules: {len(ATLAS_MODULES)}")
    print()
    for name, mod in ATLAS_MODULES.items():
        caps = ", ".join(c.value for c in mod["contributes"])
        print(f"  [{name}]")
        print(f"    Lead: {mod['lead_agent']}")
        print(f"    Desc: {mod['description']}")
        print(f"    Caps: {caps}")
        print()


def cmd_check(args):
    """检查架构完整性"""
    errors = verify_integrity()
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)
    print("Atlas integrity check: PASSED ✓")


def cmd_voice(args):
    """启动语音模式 — TODO"""
    print("Voice mode: coming soon in Phase 1")


def main():
    parser = argparse.ArgumentParser(description="Atlas — 通用人工智能体")
    parser.add_argument("--version", action="version", version="Atlas v0.1.0")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("info", help="显示架构信息")
    sub.add_parser("check", help="检查架构完整性")
    sub.add_parser("voice", help="启动语音模式")

    args = vars(parser.parse_args())
    cmd = args.pop("command", None)

    commands = {
        "info": cmd_info,
        "check": cmd_check,
        "voice": cmd_voice,
    }

    if cmd and cmd in commands:
        commands[cmd](args)
    else:
        parser.print_help()
