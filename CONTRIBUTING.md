# 贡献指南 / Contributing Guide

欢迎为 Atlas 贡献代码！以下指南帮助你快速上手。

## 项目结构 / Project Structure

```
atlas-agent/
  atlas_core/       # 核心库 (Core Integration Layer)
    __init__.py      # 模块导出
    architecture.py  # 架构定义 (接口契约)
    core.py          # Atlas 主类 (process 入口)
    router_engine.py # 路由引擎 (意图识别+Agent分派)
    memory_engine.py # 记忆引擎 (持久化存储)
    voice_engine.py  # 语音引擎 (STT/TTS)
    cli.py           # 命令行入口
  tests/             # 测试套件
  docs/              # 文档与设计文档
  examples/          # 使用示例
  webui/             # Web 用户界面
```

## 开发环境 / Development Setup

```bash
# 克隆仓库
git clone https://github.com/596600892/atlas-agent.git
cd atlas-agent

# 创建虚拟环境 (推荐 uv)
uv venv
source .venv/bin/activate

# 安装开发依赖
pip install -e ".[dev,voice,vector]"

# 运行测试
pytest -v
```

## 提交规范 / Commit Convention

使用语义化提交信息:

- `feat:` 新功能 (如 `feat: add dark mode to webui`)
- `fix:` 修复 (如 `fix: handle empty input in process()`)
- `docs:` 文档变更
- `test:` 测试变更
- `refactor:` 重构
- `chore:` 工具/配置变更

## 测试要求 / Testing Requirements

- 所有新功能必须有测试覆盖
- 运行 `pytest -v` 确保全部通过
- 测试文件位于 `tests/` 目录

## 开发流程 / Development Flow

1. Fork 或创建分支
2. 编写代码 + 测试
3. `pytest -v` 全量测试通过
4. 提交 PR
5. CI 自动检查通过后合并

## 设计原则 / Design Principles

1. **接口优先** — 修改前先看 architecture.py 的接口定义
2. **向后兼容** — 不破坏已有 API
3. **双语文档** — 所有 docstring 中英双语
4. **测试驱动** — 先写测试，后写实现
