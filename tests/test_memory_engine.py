#!/usr/bin/env python3
"""
Atlas Memory Engine — Unit Tests
记忆引擎 — 单元测试

Tests for: MemoryStore, ImportanceScorer, PruningStrategy, ContextInjector
测试内容：存储、评分、裁剪、注入、导入导出
"""

import json
import os
import tempfile
import time
import shutil

import pytest

from atlas_core.memory_engine import (
    MemoryStore,
    ImportanceScorer,
    PruningStrategy,
    ContextInjector,
    VectorSearch,
    MemoryConsolidator,
    MemoryEngine,
    create_memory_engine,
)


# ---------------------------------------------------------------------------
# Fixtures / 测试夹具
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing.
    创建临时 SQLite 数据库用于测试。"""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_memory.db")
    store = MemoryStore(db_path)
    yield store
    store.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def populated_store(temp_db):
    """Populate the store with sample memories.
    向存储中填充样本记忆数据。"""
    store = temp_db

    # Various types / 各种类型
    store.save("user_name", "Alice", type="preference", tags=["user", "identity"], importance=0.9)
    store.save("api_key_setting", "sk-abc123...", type="credential", tags=["security", "api"], importance=0.8)

    time.sleep(0.01)  # ensure different timestamps / 确保时间戳不同

    store.save("greeting", "Hello world", type="fact", tags=["general"], importance=0.1)
    store.save("reminder_meeting", "Team standup at 10am", type="event", tags=["work", "meeting"], importance=0.6)
    store.save("user_preference_theme", "Dark mode preferred", type="preference", tags=["user", "ui"], importance=0.7)

    # Memory with TTL / 带 TTL 的记忆
    store.save("temp_note", "This will expire", type="fact", tags=["temp"], importance=0.3, ttl=1)

    # Memory with no tags / 无标签的记忆
    store.save("lonely_memory", "I have no tags", type="fact", importance=0.5)

    return store


# ---------------------------------------------------------------------------
# Tests: MemoryStore — save / recall / forget / get_by_id
# ---------------------------------------------------------------------------

class TestMemoryStoreBasic:
    """Basic CRUD operations. / 基本的增删改查操作。"""

    def test_save_and_get_by_id(self, temp_db):
        """Test saving a memory and retrieving it by ID.
        测试保存记忆并通过 ID 检索。"""
        mid = temp_db.save("test_key", "test content", type="fact",
                           tags=["test"], importance=0.5)
        assert isinstance(mid, int)
        assert mid > 0

        retrieved = temp_db.get_by_id(mid)
        assert retrieved is not None
        assert retrieved["key"] == "test_key"
        assert retrieved["content"] == "test content"
        assert retrieved["type"] == "fact"
        assert retrieved["tags"] == ["test"]
        assert retrieved["importance"] == 0.5
        assert "created_at" in retrieved
        assert "access_count" in retrieved

    def test_save_update_existing_key(self, temp_db):
        """Test updating a memory with the same key overwrites it.
        测试使用相同 key 会覆盖已有记忆。"""
        mid1 = temp_db.save("dup_key", "original", type="fact", tags=[], importance=0.3)
        mid2 = temp_db.save("dup_key", "updated", type="fact", tags=["new_tag"], importance=0.9)

        # Same key should yield same ID / 相同 key 应返回相同 ID
        assert mid1 == mid2

        retrieved = temp_db.get_by_id(mid1)
        assert retrieved["content"] == "updated"
        assert retrieved["tags"] == ["new_tag"]
        assert retrieved["importance"] == 0.9

    def test_auto_importance_when_none(self, temp_db):
        """Test that importance is auto-calculated when not provided.
        测试不提供重要性时会自动计算。"""
        mid = temp_db.save("auto_importance", "This is a critical security issue", type="fact")
        retrieved = temp_db.get_by_id(mid)
        # Should have some importance > base / 应大于基础分
        assert retrieved["importance"] > 0.3

    def test_recall_basic(self, populated_store):
        """Test basic keyword recall.
        测试基本关键词召回。"""
        results = populated_store.recall("Alice")
        assert len(results) >= 1
        assert any("Alice" in r["content"] for r in results)

    def test_recall_multi_word(self, populated_store):
        """Test multi-keyword recall.
        测试多关键词召回。"""
        results = populated_store.recall("Dark mode")
        assert len(results) >= 1
        assert any("Dark" in r["content"] for r in results)

    def test_recall_tag_matching(self, populated_store):
        """Test that tags are also searched.
        测试标签也会被搜索。"""
        results = populated_store.recall("security")
        # Should match memory with "security" tag / 应匹配到带 security 标签的记忆
        assert any("sk-abc" in r["content"] for r in results)

    def test_recall_empty_query(self, populated_store):
        """Test recall with empty query returns empty.
        测试空查询返回空列表。"""
        results = populated_store.recall("")
        assert results == []
        results = populated_store.recall("   ")
        assert results == []

    def test_recall_limit(self, populated_store):
        """Test recall respects limit parameter.
        测试 recall 遵循 limit 参数。"""
        results = populated_store.recall("a", limit=2)
        assert len(results) <= 2

    def test_get_by_id_not_found(self, temp_db):
        """Test get_by_id returns None for non-existent ID.
        测试 get_by_id 对不存在的 ID 返回 None。"""
        assert temp_db.get_by_id(99999) is None

    def test_forget_by_id(self, populated_store):
        """Test forgetting a memory by ID.
        测试按 ID 删除记忆。"""
        mid = populated_store.save("delete_me", "to be deleted", type="fact")
        assert populated_store.get_by_id(mid) is not None

        deleted = populated_store.forget(memory_id=mid)
        assert deleted == 1
        assert populated_store.get_by_id(mid) is None

    def test_forget_older_than_days(self, temp_db):
        """Test forgetting memories older than N days.
        测试按天数删除旧记忆。"""
        store = temp_db

        # Create memories at known times using direct SQL
        # 用直接 SQL 在已知时间创建记忆
        now = time.time()
        with store._lock:
            cur = store._conn.cursor()
            # Memory from "30 days ago" / "30天前"的记忆
            cur.execute(
                "INSERT INTO memories (key, content, type, tags, importance, created_at, updated_at, access_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                ("old_mem", "old content", "fact", "[]", 0.3, now - 86400 * 30, now - 86400 * 30),
            )
            # Memory from "1 day ago" / "1天前"的记忆
            cur.execute(
                "INSERT INTO memories (key, content, type, tags, importance, created_at, updated_at, access_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                ("recent_mem", "recent content", "fact", "[]", 0.5, now - 86400, now - 86400),
            )
            store._conn.commit()

        # Delete memories older than 7 days / 删除7天前的记忆
        deleted = store.forget(older_than_days=7)
        assert deleted == 1  # only "old_mem" is older than 7 days / 只有 old_mem 超过7天

        # Verify old one is gone, recent one remains
        # 验证旧记忆已删除，新记忆仍在
        assert store.get_by_id(1) is None  # old_mem (id=1)
        recent = store.get_by_id(2)
        assert recent is not None  # recent_mem (id=2)
        assert recent["key"] == "recent_mem"

        # Test forget with older_than_days=0 (everything qualifies) — verify it works
        # 测试 older_than_days=0（全部符合条件） — 验证功能正常
        deleted = store.forget(older_than_days=0)
        assert deleted == 1  # the remaining recent_mem / 剩下的 recent_mem

    def test_list_types(self, populated_store):
        """Test list_types returns correct type counts.
        测试 list_types 返回正确的类型计数。"""
        types = populated_store.list_types()
        type_map = {t["type"]: t["count"] for t in types}
        assert "fact" in type_map
        assert "preference" in type_map
        assert "event" in type_map
        assert type_map["fact"] >= 3  # greeting, temp_note, lonely_memory

    def test_stats(self, populated_store):
        """Test stats returns meaningful values.
        测试 stats 返回有意义的统计值。"""
        s = populated_store.stats()
        assert s["total_count"] >= 6
        assert s["oldest"] is not None
        assert s["newest"] is not None
        assert s["avg_importance"] > 0
        assert s["types_count"] >= 3
        assert s["size_estimate_bytes"] > 0


# ---------------------------------------------------------------------------
# Tests: ImportanceScorer
# ---------------------------------------------------------------------------

class TestImportanceScorer:
    """Tests for automatic importance calculation.
    自动重要性计算测试。"""

    def test_score_content_basic(self):
        """Basic content scoring.
        基本内容评分测试。"""
        # Empty content / 空内容
        assert ImportanceScorer.score_content("") == 0.1
        assert ImportanceScorer.score_content("   ") == 0.1

        # Normal content / 普通内容
        score = ImportanceScorer.score_content("Hello world")
        assert 0.1 <= score <= 1.0

    def test_score_content_important_topics(self):
        """Important keywords get higher scores.
        重要关键词获得更高评分。"""
        normal = ImportanceScorer.score_content("Hello world")
        important = ImportanceScorer.score_content("This is a critical security issue")
        assert important >= normal

        user_info = ImportanceScorer.score_content("user_name is John and password is secret")
        assert user_info >= normal

    def test_score_content_long_content(self):
        """Longer content gets a boost.
        较长内容获得额外加分。"""
        short = ImportanceScorer.score_content("Hi")
        long_text = "word " * 100  # 100 words
        long_score = ImportanceScorer.score_content(long_text)
        assert long_score >= short

    def test_score_recency(self):
        """Recent memories get higher recency scores.
        新记忆获得更高的时间衰减分。"""
        now = time.time()
        recent = ImportanceScorer.score_recency(now - 60)  # 1 minute ago / 1分钟前
        old = ImportanceScorer.score_recency(now - 86400 * 365)  # 1 year ago / 1年前
        assert recent > old

        # Very old should floor at 0.1 / 非常旧的应降至 0.1
        ancient = ImportanceScorer.score_recency(now - 86400 * 3650)  # 10 years
        assert ancient == 0.1

    def test_score_frequency(self):
        """Frequently accessed memories get higher frequency scores.
        频繁访问的记忆获得更高频率分。"""
        never = ImportanceScorer.score_frequency(0)
        some = ImportanceScorer.score_frequency(10)
        many = ImportanceScorer.score_frequency(1000)
        assert never == 1.0
        assert some > never
        assert many >= some
        # Capped at 2.0 / 上限为 2.0
        assert many <= 2.0

    def test_combined_score(self):
        """Combined score integrates all factors.
        综合评分整合所有因素。"""
        now = time.time()
        # Important content, recent, frequently accessed / 重要内容、新、频繁访问
        high = ImportanceScorer.combined_score(
            "critical security issue with user password",
            created_at=now - 60,
            access_count=100,
        )
        # Low importance content, old, never accessed / 低重要性内容、旧、从未访问
        low = ImportanceScorer.combined_score(
            "just a random note",
            created_at=now - 86400 * 365,
            access_count=0,
        )
        assert high >= low


# ---------------------------------------------------------------------------
# Tests: TTL expiration
# ---------------------------------------------------------------------------

class TestTTLExpiration:
    """TTL (Time-To-Live) tests.
    TTL（存活时间）测试。"""

    def test_ttl_expired_removal(self, temp_db):
        """Test that expired TTL memories are removed.
        测试 TTL 过期的记忆被移除。"""
        store = temp_db
        # Create a memory with 0-second TTL (immediately expired)
        # 创建 TTL=0 的记忆（立即过期）
        mid = store.save("expire_now", "gone soon", type="fact", tags=[], ttl=0)
        assert store.get_by_id(mid) is not None  # still in DB / 仍在 DB 中

        # Force TTL check / 强制 TTL 检查
        pruner = PruningStrategy(store)
        deleted = pruner.ttl_expired()
        assert deleted >= 1
        assert store.get_by_id(mid) is None  # should be gone / 应已被删除

    def test_ttl_not_expired(self, temp_db):
        """Test that non-expired TTL memories are kept.
        测试未过期的 TTL 记忆得以保留。"""
        store = temp_db
        mid = store.save("keep_me", "still valid", type="fact", tags=[], ttl=3600)
        pruner = PruningStrategy(store)
        deleted = pruner.ttl_expired()
        assert deleted == 0
        assert store.get_by_id(mid) is not None


# ---------------------------------------------------------------------------
# Tests: PruningStrategy
# ---------------------------------------------------------------------------

class TestPruning:
    """Memory pruning tests. / 记忆裁剪测试。"""

    def test_prune_removes_low_importance(self, temp_db):
        """Test that prune removes lowest-importance memories.
        测试裁剪移除低重要性的记忆。"""
        store = temp_db

        # Save memories with varying importance / 保存不同重要性的记忆
        for i in range(20):
            imp = i / 20.0
            store.save(f"mem_{i}", f"Content {i}", type="fact", tags=[], importance=imp)

        # Prune to keep only top 5 / 裁剪保留前5条
        pruner = PruningStrategy(store)
        deleted = pruner.prune(keep_top_k=5)

        assert deleted >= 15  # 20 - 5 = 15 deleted

        # The kept ones should have highest importance / 保留的应具有最高重要性
        stats = store.stats()
        assert stats["total_count"] <= 5

    def test_prune_with_ttl_expiry_first(self, temp_db):
        """Test that prune also cleans expired TTL memories.
        测试裁剪也会清理过期 TTL 记忆。"""
        store = temp_db
        store.save("expired", "gone", type="fact", tags=[], importance=0.9, ttl=0)
        store.save("keep", "stays", type="fact", tags=[], importance=0.3, ttl=3600)

        pruner = PruningStrategy(store)
        deleted = pruner.prune(keep_top_k=100)
        assert deleted >= 1  # at least the expired one / 至少删了过期的那条

    def test_prune_no_op_when_under_limit(self, temp_db):
        """Test prune does nothing when under the limit.
        测试低于限制时裁剪不做任何事。"""
        store = temp_db
        store.save("only_one", "just me", type="fact")

        pruner = PruningStrategy(store)
        deleted = pruner.prune(keep_top_k=1000)
        assert deleted == 0

    def test_get_pruning_stats(self, temp_db):
        """Test pruning statistics.
        测试裁剪统计信息。"""
        store = temp_db
        store.save("a", "High importance", type="fact", importance=0.9)
        store.save("b", "Low importance", type="fact", importance=0.2)
        store.save("c", "Will expire", type="fact", importance=0.5, ttl=0)

        pruner = PruningStrategy(store)
        stats = pruner.get_stats()
        assert stats["total"] >= 3
        assert stats["expired_ttl_count"] >= 1
        assert stats["importance_distribution"]["high"] >= 1
        assert stats["importance_distribution"]["low"] >= 1


# ---------------------------------------------------------------------------
# Tests: ContextInjector
# ---------------------------------------------------------------------------

class TestContextInjector:
    """Context injection formatting tests.
    上下文注入格式化测试。"""

    def test_get_relevant_context_basic(self, populated_store):
        """Test that context is formatted correctly.
        测试上下文格式正确。"""
        injector = ContextInjector(populated_store)
        context = injector.get_relevant_context("Alice preference", max_tokens=500)

        assert "<atlas_memory_context>" in context
        assert "</atlas_memory_context>" in context
        assert "Alice" in context or "preference" in context

    def test_get_relevant_context_empty(self, temp_db):
        """Test empty context when no memories match.
        测试无匹配记忆时空上下文。"""
        injector = ContextInjector(temp_db)
        context = injector.get_relevant_context("zzz_nonexistent_12345")
        assert context == ""

    def test_get_relevant_context_tokens_limit(self, populated_store):
        """Test that context respects token limit.
        测试上下文遵循 token 限制。"""
        injector = ContextInjector(populated_store)
        # Very small limit / 非常小的限制
        context = injector.get_relevant_context("a", max_tokens=10)
        # Should be short / 应该很短
        assert len(context) < 10 * 4 + 100  # chars ≈ tokens * 4 + overhead

    def test_get_relevant_context_structure(self, populated_store):
        """Test the structure markers in output.
        测试输出中的结构标记。"""
        injector = ContextInjector(populated_store)
        context = injector.get_relevant_context("a", max_tokens=2000)

        if context:
            # Should have type comments / 应有类型注释
            assert "memories" in context
            # Should have key markers / 应有 key 标记
            assert "[" in context
            assert "]" in context
            # Should have importance markers / 应有重要性标记
            assert "importance=" in context

    def test_get_formatted_context_alias(self, populated_store):
        """Test that get_formatted_context works (alias).
        测试 get_formatted_context 别名正常工作。"""
        injector = ContextInjector(populated_store)
        c1 = injector.get_relevant_context("test", max_tokens=100)
        c2 = injector.get_formatted_context("test", max_tokens=100)
        assert c1 == c2


# ---------------------------------------------------------------------------
# Tests: Export / Import
# ---------------------------------------------------------------------------

class TestExportImport:
    """Export/Import backup tests.
    导入导出备份测试。"""

    def test_export_json(self, populated_store):
        """Test exporting memories to JSON.
        测试将记忆导出到 JSON。"""
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            count = populated_store.export_json(tmpfile)
            assert count >= 6

            # Verify file structure / 验证文件结构
            with open(tmpfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["version"] == "1.0"
            assert data["count"] == count
            assert len(data["memories"]) == count
        finally:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)

    def test_import_json(self, temp_db):
        """Test importing memories from JSON.
        测试从 JSON 导入记忆。"""
        # First export from populated store / 先从填充的存储导出
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            src_store = populated_store.__wrapped__ if hasattr(populated_store, '__wrapped__') else None
            # Use a fresh populated store / 使用新的填充存储
            fresh_store = populated_store.__wrapped__ if hasattr(populated_store, '__wrapped__') else populated_store

            # Actually let's just create a simple export/import test
            # 还是直接做一个简单的导入导出测试

            # Create source store and export / 创建源存储并导出
            tmpdir = tempfile.mkdtemp()
            db1 = os.path.join(tmpdir, "src.db")
            store1 = MemoryStore(db1)
            store1.save("key_a", "Content A", type="fact", tags=["x"], importance=0.5)
            store1.save("key_b", "Content B", type="preference", tags=["y"], importance=0.8)
            export_count = store1.export_json(tmpfile)
            assert export_count == 2
            store1.close()

            # Import into destination store / 导入到目标存储
            store2 = temp_db
            import_count = store2.import_json(tmpfile)
            assert import_count == 2

            # Verify memories were imported / 验证记忆已导入
            results = store2.recall("Content A", limit=10)
            assert any(r["content"] == "Content A" for r in results)
            # Verify both are there / 验证两者都在
            results_b = store2.recall("Content B", limit=10)
            assert any(r["content"] == "Content B" for r in results_b)

            shutil.rmtree(tmpdir, ignore_errors=True)
        finally:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)

    def test_import_skips_expired_ttl(self, temp_db):
        """Test that importing skips already-expired TTL memories.
        测试导入跳过已过期的 TTL 记忆。"""
        tmpfile = tempfile.mktemp(suffix=".json")

        try:
            # Create export data with expired TTL / 创建含过期 TTL 的导出数据
            data = {
                "version": "1.0",
                "exported_at": "2025-01-01T00:00:00+00:00",
                "count": 1,
                "memories": [{
                    "key": "expired_mem",
                    "content": "I am expired",
                    "type": "fact",
                    "tags": [],
                    "importance": 0.5,
                    "ttl": 100,  # expired long ago / 很久以前就过期了
                    "created_at": 50,
                    "updated_at": 50,
                    "access_count": 0,
                }],
            }
            with open(tmpfile, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Import — expired TTL memories should be skipped
            # 导入 — 过期 TTL 记忆应被跳过
            count = temp_db.import_json(tmpfile)
            assert count == 0
        finally:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)


# ---------------------------------------------------------------------------
# Tests: Cross-session search
# ---------------------------------------------------------------------------

class TestCrossSession:
    """Cross-session search tests.
    跨会话搜索测试。"""

    def test_cross_session_search(self, populated_store):
        """Test cross-session search returns results with ISO timestamps.
        测试跨会话搜索返回含 ISO 时间戳的结果。"""
        results = populated_store.cross_session_search("Alice", limit=5)
        assert len(results) >= 1
        assert "created_iso" in results[0]
        assert "updated_iso" in results[0]

    def test_cross_session_search_high_limit(self, populated_store):
        """Test cross-session search with higher default limit.
        测试跨会话搜索更高的默认限制。"""
        results = populated_store.cross_session_search("a")
        assert len(results) <= 20


# ---------------------------------------------------------------------------
# Tests: create_memory_engine factory
# ---------------------------------------------------------------------------

class TestFactory:
    """Factory function tests. / 工厂函数测试。"""

    def test_create_memory_engine(self):
        """Test the convenience factory creates all components.
        测试便捷工厂创建所有组件。"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "factory_test.db")
        try:
            store, scorer, pruner, injector = create_memory_engine(db_path)
            assert isinstance(store, MemoryStore)
            assert scorer is not None
            assert isinstance(pruner, PruningStrategy)
            assert isinstance(injector, ContextInjector)
            store.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case tests. / 边界情况测试。"""

    def test_save_empty_content(self, temp_db):
        """Test saving with empty content.
        测试保存空内容。"""
        mid = temp_db.save("empty_content", "", type="fact")
        retrieved = temp_db.get_by_id(mid)
        assert retrieved is not None
        assert retrieved["content"] == ""

    def test_save_special_characters(self, temp_db):
        """Test saving content with special characters.
        测试保存含特殊字符的内容。"""
        special = "Line1\nLine2\tTabbed\n\"Quotes\"'Single'\\Backslash"
        mid = temp_db.save("special_chars", special, type="fact")
        retrieved = temp_db.get_by_id(mid)
        assert retrieved["content"] == special

    def test_save_unicode(self, temp_db):
        """Test saving Unicode content (Chinese).
        测试保存 Unicode 内容（中文）。"""
        chinese = "你好，世界！记忆引擎测试"
        mid = temp_db.save("unicode_test", chinese, type="fact")
        retrieved = temp_db.get_by_id(mid)
        assert retrieved["content"] == chinese

    def test_save_large_content(self, temp_db):
        """Test saving large content.
        测试保存大内容。"""
        large = "Hello " * 10000  # ~60K chars
        mid = temp_db.save("large_content", large, type="fact")
        retrieved = temp_db.get_by_id(mid)
        assert retrieved is not None
        assert len(retrieved["content"]) == len(large)

    def test_multiple_tags(self, temp_db):
        """Test saving with many tags.
        测试保存多个标签。"""
        tags = [f"tag_{i}" for i in range(50)]
        mid = temp_db.save("many_tags", "content", type="fact", tags=tags)
        retrieved = temp_db.get_by_id(mid)
        assert len(retrieved["tags"]) == 50

    def test_forget_none(self, temp_db):
        """Test forget with no arguments returns 0.
        测试 forget 无参数时返回 0。"""
        assert temp_db.forget() == 0

    def test_stats_empty(self, temp_db):
        """Test stats on empty database.
        测试空数据库的统计信息。"""
        s = temp_db.stats()
        assert s["total_count"] == 0
        assert s["types_count"] == 0


# ---------------------------------------------------------------------------
# Tests: Memory Graph (link / unlink / get_memory_graph)
# ---------------------------------------------------------------------------

class TestMemoryGraph:
    """Memory graph association network tests.
    记忆图谱关联网络测试。"""

    def test_link_memories(self, temp_db):
        """Test linking two memories bidirectionally.
        测试双向关联两个记忆。"""
        mid1 = temp_db.save("node_a", "Content A", type="fact", tags=[], importance=0.5)
        mid2 = temp_db.save("node_b", "Content B", type="fact", tags=[], importance=0.5)

        result = temp_db.link_memories(mid1, mid2)
        assert result is True

        # Verify bidirectional link / 验证双向关联
        m1 = temp_db.get_by_id(mid1)
        m2 = temp_db.get_by_id(mid2)
        assert mid2 in m1["related_ids"]
        assert mid1 in m2["related_ids"]

    def test_link_self_returns_false(self, temp_db):
        """Test linking a memory to itself returns False.
        测试关联到自身返回 False。"""
        mid = temp_db.save("self_node", "Self", type="fact")
        assert temp_db.link_memories(mid, mid) is False

    def test_link_nonexistent_returns_false(self, temp_db):
        """Test linking with non-existent IDs returns False.
        测试关联不存在 ID 返回 False。"""
        mid = temp_db.save("real_node", "Real", type="fact")
        assert temp_db.link_memories(mid, 99999) is False
        assert temp_db.link_memories(99998, 99999) is False

    def test_unlink_memories(self, temp_db):
        """Test unlinking removes the bidirectional association.
        测试取消关联移除双向关联。"""
        mid1 = temp_db.save("node_a", "Content A", type="fact")
        mid2 = temp_db.save("node_b", "Content B", type="fact")
        temp_db.link_memories(mid1, mid2)

        result = temp_db.unlink_memories(mid1, mid2)
        assert result is True

        m1 = temp_db.get_by_id(mid1)
        m2 = temp_db.get_by_id(mid2)
        assert mid2 not in m1["related_ids"]
        assert mid1 not in m2["related_ids"]

    def test_unlink_nonexistent_link(self, temp_db):
        """Test unlinking memories that were never linked.
        测试取消未关联的记忆。"""
        mid1 = temp_db.save("node_a", "A", type="fact")
        mid2 = temp_db.save("node_b", "B", type="fact")
        # No link created — should still return True (no-op)
        result = temp_db.unlink_memories(mid1, mid2)
        assert result is True

    def test_get_memory_graph_basic(self, temp_db):
        """Test getting the association graph of a memory.
        测试获取记忆的关联图谱。"""
        mid1 = temp_db.save("center", "Center node", type="fact", importance=0.9)
        mid2 = temp_db.save("leaf_a", "Leaf A", type="fact", importance=0.5)
        mid3 = temp_db.save("leaf_b", "Leaf B", type="fact", importance=0.3)

        temp_db.link_memories(mid1, mid2)
        temp_db.link_memories(mid1, mid3)

        graph = temp_db.get_memory_graph(mid1, depth=1)
        assert mid1 in graph
        assert mid2 in graph
        assert mid3 in graph
        assert graph[mid1]["importance"] == 0.9

    def test_get_memory_graph_isolated(self, temp_db):
        """Test graph of an isolated memory (no links).
        测试孤立记忆的图谱（无关联）。"""
        mid = temp_db.save("loner", "Alone", type="fact")
        graph = temp_db.get_memory_graph(mid, depth=2)
        assert mid in graph
        assert graph[mid]["related"] == []

    def test_get_memory_graph_nonexistent(self, temp_db):
        """Test graph of a non-existent memory returns empty dict.
        测试不存在的记忆返回空字典。"""
        graph = temp_db.get_memory_graph(99999)
        assert graph == {}


# ---------------------------------------------------------------------------
# Tests: VectorSearch (no sentence-transformers = graceful fallback)
# ---------------------------------------------------------------------------

class TestVectorSearch:
    """Vector search tests with sentence-transformers not installed.
    向量搜索测试（sentence-transformers 未安装时的优雅回退）。"""

    def test_vector_search_unavailable(self, temp_db):
        """Test that vector search returns empty list when model unavailable.
        测试模型不可用时返回空列表。"""
        store = temp_db
        store.save("test_item", "Important thing to remember", type="fact")
        vs = VectorSearch(store)
        results = vs.search("find important things", limit=5)
        # Without sentence-transformers, should return empty list
        assert results == []

    def test_cosine_similarity(self):
        """Test pure Python cosine similarity calculation.
        测试纯 Python 余弦相似度计算。"""
        # Identical vectors / 相同向量
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert VectorSearch._cosine_similarity(a, b) == 1.0

        # Orthogonal vectors / 正交向量
        c = [0.0, 1.0, 0.0]
        assert VectorSearch._cosine_similarity(a, c) == 0.0

        # Opposite vectors / 相反向量
        d = [-1.0, 0.0, 0.0]
        assert VectorSearch._cosine_similarity(a, d) == -1.0

        # Zero vector / 零向量
        zero = [0.0, 0.0, 0.0]
        assert VectorSearch._cosine_similarity(a, zero) == 0.0

        # Partial match / 部分匹配
        e = [1.0, 1.0, 0.0]
        sim = VectorSearch._cosine_similarity(a, e)
        assert 0.7 < sim < 0.8  # cos(45°) ≈ 0.707


# ---------------------------------------------------------------------------
# Tests: MemoryConsolidator
# ---------------------------------------------------------------------------

class TestConsolidation:
    """Memory consolidation tests.
    记忆合并测试。"""

    def test_consolidate_no_duplicates(self, temp_db):
        """Test consolidation with no similar memories.
        测试无相似记忆时合并空操作。"""
        store = temp_db
        store.save("unique_1", "Completely different content here", type="fact")
        store.save("unique_2", "Another totally unrelated thing", type="fact")

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate(similarity_threshold=0.85)
        assert result["merged_count"] == 0
        assert result["deleted_count"] == 0

    def test_consolidate_duplicates(self, temp_db):
        """Test merging highly similar memories.
        测试合并高度相似的记忆。"""
        store = temp_db
        # Create two very similar memories / 创建两个非常相似的记忆
        store.save("dup_1", "This is a note about something important", type="fact",
                    tags=["important"], importance=0.9)
        store.save("dup_2", "This is a note about something important", type="fact",
                    tags=["note"], importance=0.3)

        consolidator = MemoryConsolidator(store)
        result = consolidator.consolidate(similarity_threshold=0.85)
        assert result["merged_count"] >= 1
        assert result["deleted_count"] >= 1

        # Verify the high-importance one survived / 验证高重要性的保留了
        stats = store.stats()
        assert stats["total_count"] >= 1

        # The survivor should have merged tags / 幸存者应有合并后的标签
        all_records = store.recall("important")
        assert len(all_records) >= 1

    def test_consolidate_stats(self, temp_db):
        """Test consolidation statistics.
        测试合并统计信息。"""
        store = temp_db
        store.save("a", "Hello world", type="fact", importance=0.5)
        store.save("b", "Completely different", type="fact", importance=0.5)

        consolidator = MemoryConsolidator(store)
        stats = consolidator.get_stats()
        assert stats["total"] == 2
        assert "potential_duplicates" in stats
        assert "avg_similarity" in stats


# ---------------------------------------------------------------------------
# Tests: Memory Decay (PruningStrategy.decay)
# ---------------------------------------------------------------------------

class TestMemoryDecay:
    """Memory decay tests.
    记忆衰减测试。"""

    def test_decay_old_unaccessed(self, temp_db):
        """Test decay reduces importance of old unaccessed memories.
        测试衰减降低长期未访问记忆的重要性。"""
        store = temp_db
        # Create a memory with a very old timestamp / 创建一条时间戳很旧的记忆
        now = time.time()
        with store._lock:
            cur = store._conn.cursor()
            cur.execute(
                "INSERT INTO memories (key, content, type, tags, importance, created_at, updated_at, access_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                ("old_decay", "old content not accessed", "fact", "[]", 0.8, now - 86400 * 90, now - 86400 * 90),
            )
            store._conn.commit()

        pruner = PruningStrategy(store)
        affected = pruner.decay(decay_rate=0.1, max_age_days=30)
        assert affected >= 1

        # Verify importance decreased / 验证重要性降低
        retrieved = store.recall("old_decay")
        for r in retrieved:
            if r["key"] == "old_decay":
                assert r["importance"] < 0.8
                break

    def test_decay_no_effect_on_recent(self, temp_db):
        """Test decay does not affect recent memories.
        测试衰减不影响近期记忆。"""
        store = temp_db
        mid = store.save("recent", "Recent memory", type="fact", importance=0.4)
        retrieved_orig = store.get_by_id(mid)
        orig_imp = retrieved_orig["importance"]

        pruner = PruningStrategy(store)
        # Recent memory should not decay / 近期记忆不应衰减
        affected = pruner.decay(decay_rate=0.1, max_age_days=30)

        retrieved = store.get_by_id(mid)
        assert retrieved["importance"] == pytest.approx(orig_imp, rel=1e-6)

    def test_decay_floor(self, temp_db):
        """Test that decay has a floor at 0.05.
        测试衰减下限为 0.05。"""
        store = temp_db
        now = time.time()
        with store._lock:
            cur = store._conn.cursor()
            # Already very low importance, very old / 已经很低的重要性，很旧
            cur.execute(
                "INSERT INTO memories (key, content, type, tags, importance, created_at, updated_at, access_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                ("floor_test", "barely important", "fact", "[]", 0.06, now - 86400 * 90, now - 86400 * 90),
            )
            store._conn.commit()

        pruner = PruningStrategy(store)
        pruner.decay(decay_rate=0.5, max_age_days=30)

        retrieved = store.recall("barely")
        for r in retrieved:
            if r["key"] == "floor_test":
                # Should not go below 0.05 / 不应低于 0.05
                assert r["importance"] >= 0.05
                break


# ---------------------------------------------------------------------------
# Tests: MemoryEngine container
# ---------------------------------------------------------------------------

class TestMemoryEngineContainer:
    """MemoryEngine container tests.
    MemoryEngine 容器测试。"""

    def test_container_iterable(self):
        """Test that MemoryEngine unpacks as 4 components.
        测试 MemoryEngine 可以解包为 4 个组件。"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "container_test.db")
        try:
            engine = create_memory_engine(db_path)
            assert isinstance(engine, MemoryEngine)
            store, scorer, pruner, injector = engine
            assert isinstance(store, MemoryStore)
            assert isinstance(pruner, PruningStrategy)
            assert isinstance(injector, ContextInjector)
            assert engine.vector_search is not None
            assert engine.consolidator is not None
            engine.store.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_container_extra_components(self):
        """Test that container has all 6 components accessible as attributes.
        测试容器可以通过属性访问全部 6 个组件。"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "container_extra_test.db")
        try:
            engine = create_memory_engine(db_path)
            assert hasattr(engine, 'store')
            assert hasattr(engine, 'scorer')
            assert hasattr(engine, 'pruner')
            assert hasattr(engine, 'injector')
            assert hasattr(engine, 'vector_search')
            assert hasattr(engine, 'consolidator')
            engine.store.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: related_ids in save/get_by_id/export
# ---------------------------------------------------------------------------

class TestRelatedIds:
    """Tests for related_ids field in save/get_by_id/export.
    related_ids 字段在保存/获取/导出中的测试。"""

    def test_save_with_related_ids(self, temp_db):
        """Test saving a memory with explicit related_ids.
        测试保存带显式 related_ids 的记忆。"""
        mid1 = temp_db.save("first", "First", type="fact")
        mid2 = temp_db.save("second", "Second", type="fact", related_ids=[mid1])
        retrieved = temp_db.get_by_id(mid2)
        assert mid1 in retrieved["related_ids"]

    def test_export_includes_related_ids(self, populated_store):
        """Test that export JSON includes related_ids field.
        测试导出 JSON 包含 related_ids 字段。"""
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            count = populated_store.export_json(tmpfile)
            with open(tmpfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            for mem in data["memories"]:
                assert "related_ids" in mem
                assert isinstance(mem["related_ids"], list)
        finally:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)


# Run tests directly / 直接运行测试
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
