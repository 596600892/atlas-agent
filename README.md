# Atlas — 通用人工智能体

> **「All agents build Atlas. Atlas serves all.」**
>
> 这不是某个 Agent 的独角戏，而是所有 14 个专业 Agent 联合构建的旗舰项目。
> 每个 Agent 贡献自己的核心能力模块，共同铸就一个真正的通用智能体。

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](setup.py)
[![CI](https://github.com/596600892/atlas-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/596600892/atlas-agent/actions)
[![Version](https://img.shields.io/badge/version-0.5.0-blue)](CHANGELOG.md)

---

## 愿景

Atlas 是一个 Jarvis 级的全能 AI 智能体，具备：

| 能力 | 说明 |
|------|------|
| 🎙️ **语音对话** | 自然语音交互，实时语音识别与合成 |
| 🧠 **自主进化** | 闲了就学(Idle-Learning Loop)，学了就验，验了就固，固了就开源 |
| 💾 **永久记忆** | 跨会话持久记忆，能回忆数月前的对话细节 |
| 📋 **私人秘书** | 任务管理、日程安排、信息检索、主动提醒 |
| 👁️ **多模态感知** | 文字、语音、图像、视频的全方位理解与生成 |
| 🤝 **多 Agent 协作** | 自动识别任务类型，分派给专业 Agent 处理 |
| 🌐 **WebUI + 桌面端** | 浏览器访问或 Electron 桌面应用 |

---

## 快速开始

### 安装

```bash
# 方式一：从源码安装
git clone https://github.com/596600892/atlas-agent.git
cd atlas-agent
pip install -e .

# 方式二：pip 安装（暂未发布 PyPI）
# pip install atlas-agent

# 可选：安装语音、WebUI 等附加功能
pip install -e ".[voice,webui,vector,dev]"
# 或全部安装
pip install -e ".[all]"
```

### 使用

```bash
# 1. 交互式命令行
atlas

# 2. 单次查询
atlas ask "今天市场怎么样？"
atlas ask "帮我写个3分钟短视频剧本"
atlas ask "check system health"

# 3. 查看系统信息
atlas info

# 4. 列出所有已注册 Agent
atlas agents

# 5. 启动 Web 界面（浏览器访问 http://127.0.0.1:8640）
atlas web

# 6. 启动 Electron 桌面应用
atlas electron

# 7. 记忆操作
atlas memory search "上次讨论的股票"
atlas memory consolidate

# 8. 系统自检
atlas check
```

### Docker

```bash
docker build -t atlas-agent .
docker run -it atlas-agent ask "hello"
```

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Atlas Core                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Voice    │ │  Memory  │ │  Learn   │ │  Router  │           │
│  │  Engine   │ │  Engine  │ │  Engine  │ │  Engine  │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                  │
│  ┌────┴────────────┴────────────┴────────────┴────────────────┐ │
│  │                     IntentRouter                             │ │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐ │ │
│  │  │Domain   │ │Sub-Domain│ │Agent     │ │LLM Enhancement│ │ │
│  │  │Routing  │→│Routing   │→│Dispatching│→│(Ambiguous Q)  │ │ │
│  │  └─────────┘ └──────────┘ └──────────┘ └────────────────┘ │ │
│  │              Fallback: siblings → fallback → LLM → best    │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────┐
│                 Specialized Agent Layer (14 Agents)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ Finance  │ │Creative  │ │ Market   │ │ CrossDomain        │ │
│  │ Agent    │ │Coordinator│ │ Monitor  │ │ Learner            │ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├────────────────────┤ │
│  │ Screen-  │ │ Image    │ │ Video    │ │ E-commerce         │ │
│  │ play     │ │ Agent    │ │ Agent    │ │ Agent              │ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├────────────────────┤ │
│  │ MiroFish │ │ Sentin-  │ │ DeerFlow │ │ CEO Orchestrator   │ │
│  │ Swarm    │ │ el       │ │ Ops      │ │                    │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 模块架构 — 每个 Agent 贡献一块

### 核心模块（Atlas Core）

| 模块 | 主导 Agent | 说明 | 状态 |
|------|-----------|------|------|
| **Voice Engine** | ceo-orchestrator | 语音识别(STT) + 语音合成(TTS) | ✅ v0.3.0 |
| **Memory Engine** | system-sentinel | 持久记忆层，跨会话知识索引与检索 | ✅ v0.2.0 |
| **Learn Engine** | cross-domain-learner | 空闲学习循环，自学→验证→固化→开源 | 🔄 设计阶段 |
| **Router Engine** | ceo-orchestrator | 分层路由：Domain→Sub-domain→Agent | ✅ v0.5.0 |
| **ArchComponent** | ceo-orchestrator | 统一生命周期接口 + DI + 热插拔 | ✅ v0.4.0 |
| **WebUI** | ceo-orchestrator | Flask REST API + HTML/JS 界面 + Electron | ✅ v0.5.0 |

### 路由引擎（Router Engine v2）

Atlas 的核心智能路由系统，采用分层决策架构：

```
用户输入 → Domain 识别 → Sub-Domain 识别 → Agent 分派 → 结果聚合
                                                          ↓
                                                    LLM 增强（模糊查询）
```

**三层路由:**
- **DOMAIN 层** — 粗粒度：金融、创作、监控、系统
- **SUB_DOMAIN 层** — 中粒度：股票预测→剧本写作→图像生成
- **AGENT 层** — 细粒度：精确匹配到具体 Agent

**四档置信度:**
- `HIGH (≥70%)` — 直接路由，无需 LLM
- `MEDIUM (≥40%)` — 尝试兄弟 Agent，取最高分
- `LOW (≥15%)` — 调用 LLM 增强分析
- `NONE (<15%)` — 返回通用响应或最佳猜测

**四级容错:**
`TRYSIBLINGS → FALLBACK_AGENT → LLM_AMBIGUOUS → RETURN_BEST`

### 14 个专业 Agent

| Agent | 核心能力 | GitHub |
|-------|----------|--------|
| **FinanceAgent** 📈 | 8维股票预测、因子分析、权重优化、误差学习 | [finance-agent](https://github.com/596600892/finance-agent) |
| **ScreenplayAgent** 🎬 | 剧本写作、角色开发、对话优化、故事结构 | [screenplay-agent](https://github.com/596600892/screenplay-agent) |
| **MarketMonitor** 📊 | 市场情绪检测、板块轮动、相关性跟踪 | [market-monitor](https://github.com/596600892/market-monitor) |
| **MiroFish** 🐟 | 群体智能模拟、多Agent辩论、共识形成 | [mirofish-simulator](https://github.com/596600892/mirofish-simulator) |
| **CreativeCoordinator** 🎨 | 创作流程编排、多模态资产管理 | [creative-coordinator](https://github.com/596600892/creative-coordinator) |
| **ImageAgent** 🖼️ | 多后端图像生成、风格管理、批量处理 | [image-agent](https://github.com/596600892/image-agent) |
| **VideoAgent** 🎥 | 脚本→视频管线、场景组装、字幕导出 | [video-agent](https://github.com/596600892/video-agent) |
| **EcommerceAgent** 🛒 | 商品优化、定价策略、库存管理、销售分析 | [ecommerce-agent](https://github.com/596600892/ecommerce-agent) |
| **ShortVideoOpsAgent** 📱 | 短视频策略、脚本优化、平台分析、增长分析 | [short-video-ops-agent](https://github.com/596600892/short-video-ops-agent) |
| **CrossDomainLearner** 🌐 | 24+领域扫描、前沿发现、交叉创新 | [cross-domain-learner](https://github.com/596600892/cross-domain-learner) |
| **DeerFlow** ⚙️ | 平台运维、故障分析、自动恢复、自进化修复 | [deerflow-orchestrator](https://github.com/596600892/deerflow-orchestrator) |
| **TokenBudgetAgent** 💰 | Token使用跟踪、预算管理、成本分析 | [token-budget-agent](https://github.com/596600892/token-budget-agent) |
| **SystemSentinel** 🛡️ | 服务健康监控、端口发现、智能重启 | [system-sentinel](https://github.com/596600892/system-sentinel) |
| **CEO Orchestrator** 👑 | 圆桌协议、Agent健康管理、任务调度 | [ceo-agent-orchestrator](https://github.com/596600892/ceo-agent-orchestrator) |

---

## WebUI 与桌面端

Atlas 提供三种交互界面：

### 1. WebUI（浏览器）

```bash
atlas web                    # 默认 http://127.0.0.1:8640
atlas web --port 8080        # 自定义端口
atlas web --host 0.0.0.0     # 局域网访问
```

现代聊天界面，支持：
- 实时对话（输入框 + 回车发送）
- Agent 列表查看（按能力分类）
- 路由表可视化（意图→Agent 映射）
- 深色/浅色主题切换
- 响应速度和意图置信度显示

### 2. Electron 桌面应用

```bash
# 需要 Node.js + npm
atlas electron

# 或手动启动:
# cd webui/electron && npm install && npx electron .
```

桌面窗口应用，适合长期驻留使用。

### 3. CLI 命令行

```bash
atlas                    # 交互式模式（类似 ChatGPT CLI）
atlas ask "query"        # 单次查询
atlas --voice            # 语音交互模式
```

---

## 路线图

### ✅ Phase 1 — 基石搭建 (2026 Q2)
- [x] 14 个 Agent 独立开源项目完成
- [x] GitHub 认证与代码推送
- [x] Atlas 仓库初始化与架构文档
- [x] **Voice Engine** — 集成 TTS/STT，实现语音对话
- [x] **Memory Engine** — 基于 agentmemory 的持久记忆层

### ✅ Phase 2 — 核心整合 (2026 Q3)
- [x] **Router Engine (v1)** — 基础意图识别与 Agent 分派
- [x] **Memory Engine 增强** — 语义搜索、记忆图谱、巩固合并
- [x] Atlas Core 统一入口点（CLI 命令体系）
- [x] 52 个核心测试覆盖

### ✅ Phase 3 — 语音引擎升级 (2026 Q3)
- [x] Whisper API 集成（OpenAI STT）
- [x] 自动降级到 Google 免费引擎
- [x] TTS 文件保存 + 同时播放
- [x] 5 种语音预设
- [x] 68 个测试覆盖

### ✅ Phase 4 — 架构模块增强 (2026 Q3)
- [x] ArchComponent 基类（生命周期管理）
- [x] ComponentRegistry（运行时注册 + 热插拔）
- [x] DependencyInjector（拓扑排序 + 环形检测）
- [x] SystemBlueprint（拓扑导出）
- [x] PluginLoader（动态加载）
- [x] 267 个全系统测试

### ✅ Phase 5 — 分层路由引擎 (2026 Q3)
- [x] 三层路由（Domain → Sub-Domain → Agent）
- [x] 四档置信度量化
- [x] 四级容错策略
- [x] 四种结果聚合策略
- [x] LLM 增强路由（模糊意图）
- [x] RouterComponent（ArchComponent 适配）
- [x] **WebUI + Electron 桌面应用**
- [x] **CI/CD (GitHub Actions)**
- [x] **Docker 容器化**
- [x] 299 个全系统测试

### 🔄 Phase 6 — 自主进化 (规划中)
- [ ] Learn Engine 完整实现（Idle-Learning Loop）
- [ ] 完全自主的学习→验证→固化→开源循环
- [ ] 跨 Agent 知识共享机制
- [ ] 在线学习与自我优化

### 📋 Phase 7 — 完整智能体 (未来)
- [ ] 个人秘书功能（日程、提醒、信息管理）
- [ ] 主动推荐与预警
- [ ] 长期记忆的自我管理
- [ ] 多平台部署（手机、桌面、云）

---

## 项目结构

```
atlas-agent/
├── atlas_core/           # 核心库
│   ├── __init__.py       # 模块导出 (v0.5.0)
│   ├── architecture.py   # 架构定义 + 接口契约
│   ├── core.py           # Atlas 主类 (process 入口)
│   ├── router_engine.py  # 分层路由引擎 (v2)
│   ├── memory_engine.py  # 持久记忆引擎
│   ├── voice_engine.py   # 语音引擎 (STT/TTS)
│   ├── webui.py          # WebUI Flask 后端
│   └── cli.py            # CLI 入口
├── webui/                # Web 前端 + Electron
│   ├── static/           # HTML/CSS/JS
│   ├── electron/         # Electron 桌面应用
│   └── app.py            # 独立 WebUI 启动器
├── tests/                # 测试套件 (299 个)
├── examples/             # 使用示例
├── docs/plans/           # 设计文档
├── .github/workflows/    # CI/CD
├── Dockerfile            # 容器化部署
├── CHANGELOG.md          # 版本发布日志
├── CONTRIBUTING.md       # 贡献指南
└── setup.py              # 包配置
```

---

## 设计原则

1. **每个 Agent 独立但协同** — 每个 Agent 有自己的 GitHub 仓库、独立 pip 安装、独立测试。Atlas 通过集成层将它们组合。
2. **渐进式整合** — 不重构已有的 14 个仓库，而是在它们之上建立 Atlas Core 连接器。
3. **模块可替换** — 任何模块都可被更好的实现替换，不影响整体。
4. **开源优先** — 所有代码 MIT License 开放。
5. **双语文档** — 中英双语，面向全球开发者。

---

## 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

每个 Agent 仓库独立接受贡献。Atlas Core 仓库负责协调和集成。

---

## 许可证

MIT License — 详见各仓库 LICENSE 文件。
