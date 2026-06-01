# Atlas — 通用人工智能体

> **「All agents build Atlas. Atlas serves all.」**
>
> 这不是某个Agent的独角戏，而是所有14个专业Agent联合构建的旗舰项目。
> 每个Agent贡献自己的核心能力模块，共同铸就一个真正的通用智能体。

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](setup.py)

---

## 愿景

**Atlas** 是一个Jarvis级的全能AI智能体，具备：

| 能力 | 说明 |
|------|------|
| 🎙️ **语音对话** | 自然语音交互，实时语音识别与合成，像真人一样对话 |
| 🧠 **自主进化** | 闲了就学(Idle-Learning Loop)，学了必须验证，验证通过必须固化 |
| 💾 **永久记忆** | 跨会话持久记忆，能回忆数月前的对话细节 |
| 📋 **私人秘书** | 任务管理、日程安排、信息检索、主动提醒 |
| 👁️ **多模态感知** | 文字、语音、图像、视频的全方位理解与生成 |
| 🤝 **多Agent协作** | 自动识别任务类型，分派给专业Agent处理 |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     Atlas Core                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Voice    │ │  Memory  │ │  Learn   │ │  Router  │   │
│  │  Engine   │ │  Engine  │ │  Engine  │ │  Engine  │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
└───────┼─────────────┼────────────┼────────────┼─────────┘
        │             │            │            │
┌───────┴─────────────┴────────────┴────────────┴─────────┐
│              Specialized Agent Layer                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Finance  │ │Creative  │ │ Market   │ │ Sentinel │...│
│  │ Agent    │ │Coordinator│ │ Monitor  │ │          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 模块架构 — 每个Agent贡献一块

Atlas 不是从零开始造，而是**整合已有的14个开源Agent**的能力：

### 核心模块（Atlas Core）

| 模块 | 主导Agent | 说明 | GitHub |
|------|-----------|------|--------|
| **Voice Engine** | ceo-orchestrator | 语音识别(STT) + 语音合成(TTS)，驱动自然对话 | [ceo-agent-orchestrator](https://github.com/596600892/ceo-agent-orchestrator) |
| **Memory Engine** | system-sentinel | 持久记忆层，跨会话知识索引与检索 | [system-sentinel](https://github.com/596600892/system-sentinel) |
| **Learn Engine** | cross-domain-learner | 空闲学习循环，自学→验证→固化→开源 | [cross-domain-learner](https://github.com/596600892/cross-domain-learner) |
| **Router Engine** | ceo-orchestrator | 任务识别→Agent匹配→结果聚合 | [ceo-agent-orchestrator](https://github.com/596600892/ceo-agent-orchestrator) |

### 专业Agent层

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

## 路线图

### Phase 1 — 基石搭建 (2026 Q2)
- [x] 14个Agent独立开源项目完成
- [x] GitHub认证与代码推送
- [ ] Atlas仓库初始化与架构文档
- [ ] **Voice Engine** — 集成TTS/STT，实现语音对话
- [ ] **Memory Engine** — 基于agentmemory的持久记忆层

### Phase 2 — 核心整合 (2026 Q3)
- [ ] **Router Engine** — LLM驱动的智能路由，自动识别用户意图并分派
- [ ] **Learn Engine** — Idle-Learning循环整合，各Agent共享学习成果
- [ ] **Atlas Core** 合并 → 统一入口点
- [ ] 多模态输入支持（语音→文字→图像）

### Phase 3 — 自主进化 (2026 Q4)
- [ ] 完全自主的学习→验证→固化→开源循环
- [ ] 跨Agent知识共享机制
- [ ] 在线学习与模型微调
- [ ] 浏览器/工具自主操作能力

### Phase 4 — 完整智能体 (2027 Q1)
- [ ] 个人秘书功能（日程、提醒、信息管理）
- [ ] 主动推荐与预警
- [ ] 长期记忆的自我管理
- [ ] 多平台部署（手机、桌面、云）

---

## 快速开始

```bash
# 1. 克隆14个Agent仓库
./scripts/clone_all.sh

# 2. 安装Atlas Core
pip install -e .

# 3. 配置环境
cp .env.example .env
# 编辑 .env 填入你的API Keys

# 4. 启动Atlas
atlas --voice  # 语音模式
atlas --cli    # 命令行模式

# 5. 试试看
atlas> "今天市场怎么样？"
atlas> "帮我写一个3分钟的短视频剧本"
atlas> "记得明天下午3点的会议"
```

---

## 设计原则

1. **每个Agent独立但协同** — 每个 Agent 有自己的 GitHub 仓库、独立 pip 安装、独立测试。Atlas 通过集成层将它们组合。
2. **渐进式整合** — 不重构已有的14个仓库，而是在它们之上建立 Atlas Core 连接器。
3. **模块可替换** — 任何模块都可被更好的实现替换，不影响整体。
4. **开源优先** — 所有代码 MIT License 开放。
5. **自文档化** — 代码即文档，API即契约。

---

## 贡献指南

每个Agent仓库独立接受贡献。Atlas Core 仓库负责协调和集成。

1. 在任何 Agent 仓库提交 PR
2. 在 Atlas Core 提交集成层的 PR
3. 所有代码需通过测试

---

## 许可证

MIT License — 详见各仓库 LICENSE 文件。
