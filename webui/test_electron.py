#!/usr/bin/env python3
"""Phase 6: Electron 主进程测试"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
import requests

BASE = 'http://127.0.0.1:8645'
errors = []

def check(name, ok, detail=''):
    if ok:
        print(f'  ✅ {name}')
    else:
        print(f'  ❌ {name} — {detail}')
        errors.append(name)

electron_path = os.path.expanduser('~/atlas-agent/webui/electron/main.js')

if not os.path.exists(electron_path):
    check('Electron main.js 存在', False, '文件不存在')
    sys.exit(1)

with open(electron_path) as f:
    content = f.read()

print(f'\n═══ Electron 主进程 ({len(content)}B) ═══')

checks = {
    'Tray 托盘': ('Tray' in content and 'Menu' in content),
    '全局快捷键': 'globalShortcut' in content,
    '关闭到托盘': 'closeToTray' in content or 'hide' in content.lower(),
    '窗口管理': 'BrowserWindow' in content,
    'app 生命周期': 'app.' in content,
    '窗口尺寸设置': 'width:' in content and 'height:' in content,
    'URL 加载': 'loadURL' in content or 'localhost:8645' in content,
}
for name, ok in checks.items():
    check(f'Electron: {name}', ok, '')

# 检查语法 (基本校验：大括号/括号匹配)
if checks.get(''): pass
brackets = content.count('{') == content.count('}')
parens = content.count('(') == content.count(')')
check('大括号匹配', brackets, f'{{={content.count("{")} }}={content.count("}")}')
check('括号匹配', parens, f'(={content.count("(")} )={content.count(")")}')

print(f'\n═══ Electron 测试: {len(errors)} 失败 / 7 检查项 ═══')
if errors:
    sys.exit(1)
else:
    print('全部通过 ✅')
