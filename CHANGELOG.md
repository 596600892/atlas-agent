# Changelog

All notable changes to Atlas Agent are documented here.

## [0.5.0] — 2026-06-01

### Added
- **分层路由引擎 (Phase 5)** — 全新 IntentRouter 架构
  - `RouteLevel` 三层级路由 (DOMAIN → SUB_DOMAIN → AGENT)
  - `ConfidenceLevel` 四档置信度量化 (HIGH/MEDIUM/LOW/NONE)
  - `FallbackStrategy` 四级容错 (TRYSIBLINGS/FALLBACK_AGENT/LLM_AMBIGUOUS/RETURN_BEST)
  - `AggregationStrategy` 四种聚合策略 (FIRST/BEST/MERGE/LLM_MERGE)
  - `LLMEnhancer` LLM增强路由，处理模糊/多意图查询
  - `RouterComponent` 适配 ArchComponent 生命周期接口
- 86 个全新路由引擎测试
- `RouterCapability` 枚举用于元路由决策

### Changed
- `AgentCapability` 枚举全面更新映射到 architecture.py 规范名称
- `core.py` 所有旧枚举引用迁移到新枚举名
- `test_core.py` 全部旧枚举断言更新
- 全系统测试通过数: 267 → 299

### Fixed
- core.py 中 `build_response` 方法使用废弃枚举名
- test_core.py 多测试引用已删除的枚举成员

## [0.4.0] — 2026-06-01

### Added
- **Architecture 模块增强 (Phase 4)**
  - `ArchComponent` 基类 — 统一生命周期接口 (init/shutdown/restart/health)
  - `ComponentRegistry` — 运行时组件注册与热插拔
  - `DependencyInjector` — 拓扑排序自动注入，环形依赖检测
  - `SystemBlueprint` — 完整系统拓扑导出
  - `PluginLoader` — 动态加载 Python 模块
- 49 个 Architecture 测试

### Changed
- 核心引擎行数: 230 → 900
- 全系统测试数: 267

## [0.3.0] — 2026-06-01

### Added
- **Voice Engine 在线升级 (Phase 3)**
  - Whisper API 集成 (OpenAI STT) + 自动降级到 Google 免费引擎
  - `save_to_file` TTS 方法 (macOS `say` 命令)
  - `speak_and_save` — 同时播放并保存音频
  - 5 个语音预设 (PRESETS)
- 16 个新语音测试

### Changed
- 引擎行数: 1170 → 1390
- 测试数: 52 → 68

## [0.2.0] — 2026-06-01

### Added
- **Memory Engine (Phase 2)**
  - 持久化记忆存储 (JSON + SQLite)
  - `agentmemory` MCP 集成 (跨会话搜索与召回)
  - 记忆巩固与合并
  - 标签索引系统
- 路由引擎基础版 (旧版 IntentRouter)
- `Atlas` 核心类 `process()` 方法
- CLI 命令: `ask`, `info`, `agents`, `memory`, `check`
- `create_atlas()` 工厂函数
- 52 个核心测试

## [0.1.0] — 2026-06-01

### Added
- 项目初始化
- `ArchComponent` 设计文档
- `ComponentState` 生命周期枚举
- 基础项目骨架: setup.py, entry_points
- 14 个 Agent 注册表定义
