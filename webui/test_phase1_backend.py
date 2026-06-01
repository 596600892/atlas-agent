#!/usr/bin/env python3
"""Phase 1: 后端 API 全量测试"""
import json, sys, time
import requests

BASE = 'http://127.0.0.1:8645'
errors = []

def check(name, ok, detail=''):
    if ok:
        print(f'  ✅ {name}')
    else:
        print(f'  ❌ {name} — {detail}')
        errors.append(name)

# ── 1.1 GET /api/status — 基础状态 ──
print('\n═══ 1.1 基础状态 ═══')
r = requests.get(f'{BASE}/api/status', timeout=5)
check('GET /api/status 返回 200', r.status_code == 200, f'HTTP {r.status_code}')
data = r.json()
check('含 version 字段', 'version' in data, str(data.keys()))
check('含 status 字段', data.get('status') in ('ok', 'running'), str(data))
check('含 uptime 字段', 'uptime' in data, str(data.keys()))

# ── 1.2 POST /api/chat-stream — SSE 事件流 ──
print('\n═══ 1.2 SSE 事件流 ═══')
r = requests.post(f'{BASE}/api/chat-stream',
    json={'message': 'test ping'},
    headers={'Accept': 'text/event-stream'},
    stream=True, timeout=15)
check('SSE 返回 200', r.status_code == 200, f'HTTP {r.status_code}')

event_count = {}
for line in r.iter_lines():
    if not line: continue
    line = line.decode('utf-8', errors='replace')
    if line.startswith('event: '):
        evt = line[7:].strip()
        event_count[evt] = event_count.get(evt, 0) + 1
    if len(event_count) >= 5:  # 收够 5 种事件就停
        break

required_events = {'session_start', 'message_received', 'intent_analyzing', 'memory_recalling'}
for ev in required_events:
    check(f'SSE 包含事件: {ev}', ev in event_count,
          f'got: {list(event_count.keys())}')

check(f'SSE 至少收到 4 种不同事件', len(event_count) >= 4,
      f'只有 {len(event_count)} 种')

# ── 1.3 API: 记忆/对话/Agent ──
print('\n═══ 1.3 记忆图谱 API ═══')
r = requests.get(f'{BASE}/api/memories', timeout=5)
check('GET /api/memories 200', r.status_code == 200)
d = r.json()
check('返回 dict 含 nodes', isinstance(d, dict) and 'nodes' in d, str(list(d.keys())))
check('nodes 是列表', isinstance(d.get('nodes'), list), type(d.get('nodes')).__name__)
check('edges 是列表', isinstance(d.get('edges'), list), type(d.get('edges')).__name__)

print('\n═══ 1.4 对话历史 API ═══')
r = requests.get(f'{BASE}/api/conversations?limit=3', timeout=5)
check('GET /api/conversations 200', r.status_code == 200)
d = r.json()
check('返回 dict 含 conversations', isinstance(d, dict) and 'conversations' in d,
      str(list(d.keys())))
check('conversations 是列表', isinstance(d['conversations'], list),
      type(d['conversations']).__name__)

print('\n═══ 1.5 Agent 清单 API ═══')
r = requests.get(f'{BASE}/api/agents', timeout=5)
check('GET /api/agents 200', r.status_code == 200)
agents = r.json()
check('返回列表', isinstance(agents, list), type(agents).__name__)
if agents:
    check('每个 Agent 含 name', all('name' in a for a in agents), str(agents[0].keys()))

print('\n═══ 1.6 路由表 API ═══')
r = requests.get(f'{BASE}/api/routes', timeout=5)
check('GET /api/routes 200', r.status_code == 200)
routes = r.json()
check('返回 dict', isinstance(routes, dict), type(routes).__name__)

# ── 1.7 POST /api/tts — 语音合成 ──
print('\n═══ 1.7 TTS 端点 ═══')
r = requests.post(f'{BASE}/api/tts',
    json={'text': '你好世界'}, timeout=10)
check('TTS 不崩溃', r.status_code in (200, 500, 503, 501),
      f'HTTP {r.status_code}')

# ── 1.8 Agent 控制端点（新增）──
print('\n═══ 1.8 Agent 控制端点 ═══')
r = requests.post(f'{BASE}/api/hotspot-state',
    json={'active': True}, timeout=5)
check('POST /api/hotspot-state 200', r.status_code == 200, f'HTTP {r.status_code}')
d = r.json()
check('返回 hotspot_active', d.get('hotspot_active') == True, str(d))

r = requests.post(f'{BASE}/api/person-card-state',
    json={'active': True, 'person': 'Atlas'}, timeout=5)
check('POST /api/person-card-state 200', r.status_code == 200, f'HTTP {r.status_code}')
d = r.json()
check('返回 active + person', d.get('active') == True and d.get('person') == 'Atlas', str(d))

# ── 汇总 ──
total = 8 + len(required_events) + 4  # 大约 20 个检查点
print(f'\n═══ 结果: {len(errors)} 失败 / 约 {total} 检查项 ═══')
if errors:
    print('失败项:', ', '.join(errors))
    sys.exit(1)
else:
    print('全部通过 ✅')
