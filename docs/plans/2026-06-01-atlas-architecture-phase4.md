# Atlas Phase 4: Architecture Module Enhancement

## Goal
将 architecture.py 从 230 行蓝图文档升级为 800+ 行的**运行时系统骨架** — 组件注册、热插拔、生命周期管理、依赖注入。

## Changes

### 1. ComponentRegistry — 运行时组件注册表
- `register(component)` / `unregister(name)` / `get(name)` / `list()`
- 组件热插拔：运行时注册/注销，自动依赖校验

### 2. ComponentLifecycle — 组件生命周期
- 状态机: UNINITIALIZED → INITIALIZING → RUNNING → STOPPING → STOPPED → ERROR
- `start()` / `stop()` / `restart()` / `health()`
- 健康检查标准接口

### 3. DependencyInjector — 依赖注入
- 组件声明 `requires` 列表，注入器自动解析依赖图
- 环形依赖检测
- 启动顺序排序（拓扑排序）

### 4. SystemBlueprint — 系统蓝图
- 从注册表导出完整拓扑（节点+边列表）
- 导出 JSON 供 CLI/Dashboard 使用
- 组件依赖图可视化数据

### 5. PluginLoader — 热加载外部模块
- 从目录动态加载 Python 模块作为插件
- 插件自动注册到 ComponentRegistry

### 6. 测试套件
- 注册/注销测试
- 生命周期状态机测试
- 依赖注入测试（含环形检测）
- 蓝图导出测试
- 插件加载测试

### 7. __init__.py 和 cli.py 更新
- architecture.py 新类导出
- CLI 新增 `atlas system info` / `atlas system blueprint`

## Files
- `atlas_core/architecture.py` — 主要修改（230→~900行）
- `tests/test_architecture.py` — 新增测试（~40个）
- `atlas_core/__init__.py` — 更新导出
- `atlas_core/cli.py` — 新增子命令
- `setup.py` — 版本升至 0.4.0
