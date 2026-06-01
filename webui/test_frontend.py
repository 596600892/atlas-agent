#!/usr/bin/env python3
"""Phase 2-6: 前端测试 v2 — 精准版"""
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

# ── 2.1 静态资源加载 ──
print('\n═══ 2.1 静态资源加载 ═══')
static_files = {
    '/': 'text/html',
    '/static/style.css': 'text/css',
    '/static/app.js': 'javascript',
    '/static/api-client.js': 'javascript',
    '/static/themes.js': 'javascript',
    '/static/graph.js': 'javascript',
    '/static/chat.js': 'javascript',
    '/static/thought-stream.js': 'javascript',
    '/static/voice-panel.js': 'javascript',
    '/static/profile-panel.js': 'javascript',
    '/static/hotspot-earth.js': 'javascript',
}
for path, ctype_hint in static_files.items():
    r = requests.get(f'{BASE}{path}', timeout=5)
    ctype = r.headers.get('Content-Type', '')
    check(f'{path} 200 OK', r.status_code == 200, f'HTTP {r.status_code} {ctype}')

# ── 2.2 HTML 结构 ──
print('\n═══ 2.2 HTML 结构 ═══')
r = requests.get(f'{BASE}/', timeout=5)
html = r.text
html_lower = html.lower()
checks = {
    '力导向图 canvas': '<canvas' in html and 'graph' in html_lower,
    '聊天输入框': 'consoleInput' in html,
    '语音面板': 'voicePanel' in html and 'voice-canvas' in html,
    '热点面板 (3D地球)': 'hotspotPanel' in html and 'earth' in html_lower,
    '资料面板': 'profileContainer' in html,
    '主题系统 (6种)': html.count('theme-dot') >= 6,
    '设置弹窗': 'settingsOverlay' in html,
    '缩放控制': 'zoomSlider' in html,
}
for name, ok in checks.items():
    check(f'HTML 结构: {name}', ok, '')

# ── 2.3 JS 引用清单 ──
print('\n═══ 2.3 JS 引用 ═══')
js_refs = re.findall(r'<script[^>]+src="([^"]+)"', html)
check(f'页面引用 JS 文件 ({len(js_refs)})', len(js_refs) >= 9, str(js_refs))

# ── 2.4 CSS 存在性 ──
print('\n═══ 2.4 CSS 样式检查 ═══')
r = requests.get(f'{BASE}/static/style.css', timeout=5)
css = r.text
css_len = len(css)
check(f'CSS 文件大小 ({css_len}B)', css_len > 5000, f'仅 {css_len}B')
for keyword in ['voice', 'hotspot', 'profile', 'animation', 'blur']:
    check(f'CSS 含关键字: {keyword}', keyword in css, '')

# ── 2.5 JS 语法和大小 ──
print('\n═══ 2.5 JS 文件完整性 ═══')
js_files = ['api-client.js', 'themes.js', 'graph.js', 'chat.js', 'thought-stream.js',
            'voice-panel.js', 'profile-panel.js', 'hotspot-earth.js', 'app.js']
min_sizes = {'api-client.js': 1000, 'themes.js': 500, 'graph.js': 5000,
             'chat.js': 3000, 'thought-stream.js': 1500, 'voice-panel.js': 5000,
             'profile-panel.js': 3000, 'hotspot-earth.js': 8000, 'app.js': 5000}
for jsf in js_files:
    r = requests.get(f'{BASE}/static/{jsf}', timeout=5)
    size = len(r.text)
    expected = min_sizes[jsf]
    check(f'{jsf} ({size}B >= {expected}B)', size >= expected, f'仅 {size}B')

# ── 2.6 API 端点在前端的引用 ──
print('\n═══ 2.6 API 引用检查 ═══')
# 收集所有 JS 文件内容
all_js = ''
for jsf in js_files:
    r = requests.get(f'{BASE}/static/{jsf}', timeout=5)
    all_js += r.text + '\n'

api_refs = ['/api/chat-stream', '/api/chat', '/api/memories']
for api in api_refs:
    check(f'JS 引用 {api}', api in all_js, f'not found in any JS')

# ── 汇总 ──
print(f'\n═══ 前端测试结果: {len(errors)} 失败 / 约 35 检查项 ═══')
if errors:
    print('失败项:', ', '.join(errors))
    sys.exit(1)
else:
    print('全部通过 ✅')
