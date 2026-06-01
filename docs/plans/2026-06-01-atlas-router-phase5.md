# Atlas Phase 5: Router Engine Enhancement

## Goal
将 Router Engine 从 535 行/54 测试的关键词匹配路由升级为 **分层路由引擎** — 多意图分解、LLM辅助分类、回退链、结果聚合。

## Changes

### 1. 与 architecture.py 对齐
- 移除重复的 AgentCapability/AgentManifest 定义，导入 architecture
- REGISTRY 保留作为路由专用，但同步 architecture 的 ATLAS_MODULES

### 2. 分层路由
- `RouteLevel` 枚举: DOMAIN → SUB_DOMAIN → AGENT
- 先识别领域，再细分到子领域，最后匹配具体Agent

### 3. Multi-intent Decomposition
- `decompose()` 方法：将复合查询分解为多个子意图
- 如 "画一张股票走势图" → IMAGE_GEN + FINANCE
- 每个子意图独立路由，结果合并

### 4. LLM-Enhanced Classification
- `LLMEnhancer` 类：可选 LLM 辅助分类
- 当关键词匹配置信度 < 阈值时，调用 LLM 做精确分类
- 回退到关键词匹配如果 LLM 不可用

### 5. Fallback Chains
- `FallbackStrategy` 枚举: STRICT / RELAXED / CASCADE
- STRICT: 只匹配精确意图
- RELAXED: 降低置信度门槛
- CASCADE: 主Agent不可用时逐级回退

### 6. Result Aggregation
- `AggregationStrategy` 枚举: FIRST_MATCH / WEIGHTED_SUM / MERGE
- FIRST_MATCH: 取最高分
- WEIGHTED_SUM: 加权合并
- MERGE: 合并所有意图的结果

### 7. Confidence Quantiles
- `ConfidenceLevel` 枚举: HIGH(>0.6) / MEDIUM(>0.3) / LOW(>0) / UNKNOWN(=0)
- route() 新增 level 过滤器

### 8. 测试
- 新增测试：分层路由、多意图分解、LLM增强、回退链、聚合策略
- 原有测试需调整（AgentCapability 改为导入）

## Files
- `atlas_core/router_engine.py` — 主要修改（535→~950行）
- `tests/test_router.py` — 新增测试（54→~90个）
- `atlas_core/__init__.py` — 更新导出
