# Atlas Memory Engine — Phase 2 实施计划

> **Goal:** 将记忆引擎从「关键词匹配」升级为「语义搜索 + 记忆图谱 + 自动合并 + 智能衰减」
>
> **架构:** 零依赖核心 + 可选向量搜索增强，向后兼容

**核心升级：**
1. 记忆引擎：向量搜索（可选 sentence-transformers, 回退关键词）
2. 记忆引擎：记忆合并（difflib 检测相似记忆）
3. 记忆引擎：记忆图谱（related_ids 关联字段）
4. 记忆引擎：记忆衰减（按访问频率时间降权）
5. 测试：新增 ~30 测试
6. CLI：支持语义搜索和图谱查询
7. setup.py：添加 `[semantic]` extra
8. 推送 GitHub

---

### Task 1: 添加向量搜索（可选依赖，回退关键词）

**Objective:** 支持语义向量搜索，sentence-transformers 可用时自动启用，否则回退原有关键词搜索

**Files:**
- Modify: `atlas_core/memory_engine.py`

**实现要点：**
- 添加 `VectorSearch` 类（可选初始化，检测 `sentence_transformers` 是否可用）
- `MemoryStore.semantic_recall()` 方法：调用向量搜索，无向量时回退 `recall()`
- embedding 模型使用 `all-MiniLM-L6-v2`（轻量，~80MB）
- 向量存储在单独的 SQLite 表 `memory_embeddings(memory_id, embedding BLOB)` 中
- 余弦相似度计算用纯 Python（numpy 可选，回退纯 math 实现）

---

### Task 2: 添加记忆合并（Memory Consolidation）

**Objective:** 自动检测并合并相似/重复记忆

**Files:**
- Modify: `atlas_core/memory_engine.py`

**实现要点：**
- 添加 `MemoryConsolidator` 类
- `consolidate()` 方法扫描所有记忆，用 difflib.SequenceMatcher 检测高相似度（>0.85）的记忆对
- 合并策略：保留重要性更高的记忆，合并 tags，内容拼接
- 低重要性重复记忆被标记删除
- 添加 `get_consolidation_stats()` 查看合并统计

---

### Task 3: 添加记忆图谱（Memory Graph）

**Objective:** 通过 `related_ids` 字段建立记忆间关联

**Files:**
- Modify: `atlas_core/memory_engine.py`

**实现要点：**
- 在 memories 表中添加 `related_ids TEXT DEFAULT '[]'` 字段（JSON 数组）
- 添加 `link_memories(id1, id2)` 方法双向关联
- 添加 `unlink_memories(id1, id2)` 方法取消关联
- 添加 `get_memory_graph(memory_id, depth=2)` 方法递归获取关联网络
- 在 `save()` 中，自动检测与新内容高度相关的已有记忆并建立关联

---

### Task 4: 添加记忆衰减（Memory Decay）

**Objective:** 未访问的记忆随时间逐渐降权

**Files:**
- Modify: `atlas_core/memory_engine.py`

**实现要点：**
- 在 `PruningStrategy` 中添加 `decay(decay_rate=0.1)` 方法
- 对超过 30 天未访问且 importance < 0.5 的记忆，降低 importance
- 衰减公式：`new_importance = importance * (1 - decay_rate * days_since_last_access / 30)`
- min floor 为 0.05（不给到0，保留一丝可能性）
- 返回受影响的记忆数量

---

### Task 5: 更新测试

**Objective:** 为所有新功能添加测试，完整覆盖

**Files:**
- Modify: `tests/test_memory_engine.py`

**测试要点：**
- `VecSearchAvailable` / `VecSearchUnavailable` — 向量搜索可用/不可用测试
- `TestSemanticRecall` — 语义搜索基本测试
- `TestConsolidation` — 合并检测、合并执行、合并统计
- `TestMemoryGraph` — 关联建立、递归获取、取消关联
- `TestMemoryDecay` — 衰减计算、长期未访问衰减
- 新增 ~25-30 测试，总数从 43 扩展到 ~70+

---

### Task 6: 更新 CLI

**Objective:** CLI 支持语义搜索和图谱查询

**Files:**
- Modify: `atlas_core/cli.py`

**实现要点：**
- `atlas memory search --semantic <query>` — 语义搜索
- `atlas memory graph <id>` — 显示记忆图谱
- `atlas memory consolidate` — 执行合并
- `atlas memory prune --decay` — 带衰减的裁剪

---

### Task 7: 更新 setup.py + 提交推送

**Objective:** 添加可选依赖配置，提交推送GitHub

**Files:**
- Modify: `setup.py`
- Modify: `README.md` (可选)

**实现要点：**
- `extras_require["semantic"] = ["sentence-transformers>=2.2"]`
- `git add && git commit -m "feat: Phase 2 — semantic search, memory graph, consolidation, decay"`
- `git push origin main`
