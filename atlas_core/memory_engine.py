#!/usr/bin/env python3
"""
Atlas Memory Engine — 记忆引擎
=================================

持久记忆存储 (SQLite) / 重要性评分 / 自动裁剪 / 上下文注入 / 导入导出

Uses only Python stdlib — no external dependencies.
完全使用 Python 标准库，无外部依赖。
"""

import json
import re
import sqlite3
import time
import os
import shutil
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Reuse the MemoryEntry dataclass from architecture for compatibility
# 复用 architecture 中定义的 MemoryEntry 以保证兼容
from atlas_core.architecture import MemoryEntry


# ---------------------------------------------------------------------------
# 默认配置
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "atlas_memory.db")
DEFAULT_IMPORTANT_TOPICS = [
    "user preference", "user preference", "user_name", "critical", "important",
    "urgent", "favorite", "priority", "remember this", "don't forget",
    "用户偏好", "用户名", "关键", "重要", "紧急", "收藏", "优先级", "记住",
    "security", "password", "api_key", "token", "credential",
    "安全", "密码", "密钥", "令牌", "凭证",
    "goal", "objective", "mission", "target",
    "目标", "任务", "使命", "指标",
]


# ---------------------------------------------------------------------------
# MemoryStore — 核心持久存储 (SQLite)
# ---------------------------------------------------------------------------

class MemoryStore:
    """
    Persistent memory storage backed by SQLite.
    基于 SQLite 的持久记忆存储。

    Thread-safe via threading lock.
    通过 threading.Lock 实现线程安全。
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, auto_prune: bool = True):
        self.db_path = os.path.abspath(db_path)
        self._lock = threading.Lock()
        self._auto_prune = auto_prune

        # 确保数据库目录存在 / ensure DB directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    # -----------------------------------------------------------------------
    # 内部: 建表 / internal: table initialization
    # -----------------------------------------------------------------------

    def _init_db(self):
        """Create tables if they don't exist. / 如果表不存在则创建。"""
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key         TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    type        TEXT NOT NULL DEFAULT 'fact',
                    tags        TEXT NOT NULL DEFAULT '[]',
                    importance  REAL NOT NULL DEFAULT 0.5,
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    ttl         REAL        -- NULL = 永久 / permanent
                );

                CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

                CREATE TABLE IF NOT EXISTS memory_tags (
                    memory_id INTEGER NOT NULL,
                    tag       TEXT NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag);
            """)
            self._conn.commit()

    # -----------------------------------------------------------------------
    # 写操作 / write operations
    # -----------------------------------------------------------------------

    def save(
        self,
        key: str,
        content: str,
        type: str = "fact",
        tags: Optional[list[str]] = None,
        importance: Optional[float] = None,
        ttl: Optional[int] = None,
    ) -> int:
        """
        Save a new memory or update an existing one by key.
        保存新记忆，若 key 已存在则更新。

        Args:
            key: 唯一标识符 / unique identifier
            content: 记忆内容 / memory content (text)
            type: 记忆类型 / memory type (fact, preference, pattern, event, ...)
            tags: 标签列表 / list of tags
            importance: 重要性 0-1 / importance score 0-1 (None=auto-score)
            ttl: 存活时间(秒) / time-to-live in seconds (None=永久)

        Returns:
            memory_id: 新记忆的 ID / the new memory's ID
        """
        if importance is None:
            importance = ImportanceScorer.score_content(content)

        tags = tags or []
        now = time.time()
        ttl_expire = now + ttl if ttl is not None else None

        with self._lock:
            cur = self._conn.cursor()

            # Check if key already exists / 检查 key 是否已存在
            cur.execute("SELECT id FROM memories WHERE key = ?", (key,))
            row = cur.fetchone()

            if row:
                memory_id = row["id"]
                cur.execute(
                    """UPDATE memories SET content=?, type=?, tags=?, importance=?,
                       updated_at=?, ttl=?, access_count=0
                       WHERE id=?""",
                    (content, type, json.dumps(tags), importance, now, ttl_expire, memory_id),
                )
            else:
                cur.execute(
                    """INSERT INTO memories (key, content, type, tags, importance,
                       created_at, updated_at, access_count, ttl)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (key, content, type, json.dumps(tags), importance, now, now, ttl_expire),
                )
                memory_id = cur.lastrowid

            # Update tags table / 更新标签表
            cur.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
            for tag in tags:
                cur.execute(
                    "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory_id, tag),
                )

            self._conn.commit()

        return memory_id

    # -----------------------------------------------------------------------
    # 读操作 / read operations
    # -----------------------------------------------------------------------

    def recall(self, query: str, limit: int = 10) -> list[dict]:
        """
        Semantic-like search using keyword matching + tag filtering.
        语义级搜索：关键词匹配 + 标签过滤。

        Performs:
          1. Full-text LIKE search on content and key
          2. Tag-based filtering from the query
          3. Sorts by importance desc, then created_at desc

        Args:
            query: 搜索关键词 / search keywords
            limit: 最大返回条数 / max results

        Returns:
            list of memory dicts (each containing all MemoryEntry fields + id, access_count)
        """
        query = query.strip()
        if not query:
            return []

        with self._lock:
            cur = self._conn.cursor()

            # Build keyword search: split query into words, match any
            # 关键词拆解：按空格分词，匹配任一即可
            words = [w.strip() for w in re.split(r'[\s,，、]+', query) if w.strip()]
            keyword_conditions = []
            params = []
            for w in words[:10]:  # 最多10个关键词 / max 10 keywords
                like_pattern = f"%{w}%"
                keyword_conditions.append(
                    "(memories.content LIKE ? OR memories.key LIKE ?)"
                )
                params.extend([like_pattern, like_pattern])

            # Also try to match tags / 同时也尝试匹配标签
            tag_conditions = []
            for w in words[:5]:
                tag_conditions.append("memory_tags.tag LIKE ?")
                params.append(f"%{w}%")

            where_clause = " OR ".join(keyword_conditions + tag_conditions)

            if keyword_conditions or tag_conditions:
                # Need LEFT JOIN for tag search / 需要 LEFT JOIN 来支持标签搜索
                sql = f"""
                    SELECT DISTINCT memories.*
                    FROM memories
                    LEFT JOIN memory_tags ON memories.id = memory_tags.memory_id
                    WHERE ({where_clause})
                    ORDER BY memories.importance DESC, memories.created_at DESC
                    LIMIT ?
                """
                params.append(limit)
            else:
                sql = """
                    SELECT * FROM memories
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """
                params = [limit]

            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for row in rows:
                d = dict(row)
                d["tags"] = json.loads(d["tags"]) if isinstance(d.get("tags"), str) else (d.get("tags") or [])
                results.append(d)

            # Bump access_count for retrieved memories / 增加检索到的记忆的访问次数
            ids = [r["id"] for r in results]
            for mid in ids:
                cur.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
                    (mid,),
                )
            self._conn.commit()

        return results

    def get_by_id(self, memory_id: int) -> Optional[dict]:
        """
        Exact retrieval by memory ID.
        根据记忆 ID 精确检索。

        Also bumps access_count.
        同时增加访问计数。
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cur.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["tags"] = json.loads(d["tags"]) if isinstance(d.get("tags"), str) else (d.get("tags") or [])
            # Bump access / 增加访问计数
            cur.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
                (memory_id,),
            )
            self._conn.commit()
        return d

    # -----------------------------------------------------------------------
    # 删除操作 / delete operations
    # -----------------------------------------------------------------------

    def forget(self, memory_id: Optional[int] = None, older_than_days: Optional[int] = None) -> int:
        """
        Delete a memory by ID or by age.
        按 ID 或按时间删除记忆。

        Args:
            memory_id: 精确删除某条 / delete a specific memory by ID
            older_than_days: 删除 N 天前的记忆 / delete memories older than N days

        Returns:
            删除条数 / number of deleted rows
        """
        with self._lock:
            cur = self._conn.cursor()
            if memory_id is not None:
                cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            elif older_than_days is not None:
                cutoff = time.time() - older_than_days * 86400
                cur.execute("DELETE FROM memories WHERE created_at < ?", (cutoff,))
            else:
                return 0
            deleted = cur.rowcount
            self._conn.commit()
        return deleted

    # -----------------------------------------------------------------------
    # 统计 / statistics
    # -----------------------------------------------------------------------

    def list_types(self) -> list[dict]:
        """
        Return all memory types and their counts.
        返回所有记忆类型及其计数。

        Returns:
            [{"type": "fact", "count": 42}, ...]
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT type, COUNT(*) as count FROM memories GROUP BY type ORDER BY count DESC"
            )
            return [dict(row) for row in cur.fetchall()]

    def stats(self) -> dict:
        """
        Overall memory statistics.
        整体记忆统计。

        Returns dict with: total_count, oldest (timestamp), newest (timestamp),
        size_estimate_bytes, types_count, avg_importance.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(*) as total_count,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest,
                    AVG(importance) as avg_importance,
                    COUNT(DISTINCT type) as types_count
                FROM memories
            """)
            row = dict(cur.fetchone())

            # Estimate database file size / 估算数据库文件大小
            try:
                row["size_estimate_bytes"] = os.path.getsize(self.db_path)
            except OSError:
                row["size_estimate_bytes"] = 0

            return row

    # -----------------------------------------------------------------------
    # 导入导出 / export & import
    # -----------------------------------------------------------------------

    def export_json(self, filepath: str) -> int:
        """
        Export all memories to a JSON file (for backup).
        将所有记忆导出到 JSON 文件（用于备份）。

        Returns:
            导出条数 / number of exported records
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM memories ORDER BY id")
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if isinstance(r.get("tags"), str):
                    r["tags"] = json.loads(r["tags"])

        data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "memories": rows,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return len(rows)

    def import_json(self, filepath: str, merge: bool = True) -> int:
        """
        Import memories from a JSON backup file.
        从 JSON 备份文件导入记忆。

        Args:
            filepath: JSON 文件路径 / path to JSON file
            merge: 若 True 且 key 冲突则覆盖，否则跳过 / if True, overwrite on key conflict

        Returns:
            导入条数 / number of imported records
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported = 0
        for mem in data.get("memories", []):
            key = mem.get("key")
            content = mem.get("content", "")
            mtype = mem.get("type", "fact")
            tags = mem.get("tags") or []
            importance = mem.get("importance", 0.5)

            # Only set TTL if it hasn't expired / 仅在未过期时设置 TTL
            ttl_value = None
            raw_ttl = mem.get("ttl")
            if raw_ttl is not None:
                remaining = raw_ttl - time.time()
                if remaining > 0:
                    ttl_value = int(remaining)
                else:
                    continue  # skip expired memories / 跳过已过期的记忆

            self.save(key=key, content=content, type=mtype,
                      tags=tags, importance=importance, ttl=ttl_value)
            imported += 1

        return imported

    # -----------------------------------------------------------------------
    # 跨会话搜索 / cross-session search
    # -----------------------------------------------------------------------

    def cross_session_search(self, query: str, limit: int = 20) -> list[dict]:
        """
        Search across all sessions/contexts. Same as recall but with higher limit
        and includes debug info about when the memory was created.
        跨所有会话/上下文搜索。与 recall 相同但限制更高，
        并包含创建时间等调试信息。

        This method is useful when the agent needs to find information
        from previous conversations.
        当 agent 需要从之前的对话中查找信息时，此方法非常有用。
        """
        results = self.recall(query, limit=limit)
        # Add human-readable timestamps / 添加人类可读的时间戳
        for r in results:
            r["created_iso"] = datetime.fromtimestamp(
                r["created_at"], tz=timezone.utc
            ).isoformat()
            r["updated_iso"] = datetime.fromtimestamp(
                r["updated_at"], tz=timezone.utc
            ).isoformat() if r.get("updated_at") else None
        return results

    # -----------------------------------------------------------------------
    # 生命周期管理 / lifecycle
    # -----------------------------------------------------------------------

    def close(self):
        """Close the database connection. / 关闭数据库连接。"""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# ImportanceScorer — 自动重要性计算
# ---------------------------------------------------------------------------

class ImportanceScorer:
    """
    Automatic importance calculation for memories.
    记忆的自动重要性计算。

    Three factors:
      1. Content-based: important keywords → higher score
      2. Recency-based: newer memories get a time decay boost
      3. Frequency-based: frequently accessed memories get higher score
    """

    # 重要主题关键词列表 / list of important topic keywords
    IMPORTANT_TOPICS = DEFAULT_IMPORTANT_TOPICS

    @classmethod
    def score_content(cls, content: str, topics: Optional[list[str]] = None) -> float:
        """
        Score content based on important keyword mentions.
        根据重要关键词对内容评分。

        Returns a float in [0.1, 1.0].
        """
        if not content or not content.strip():
            return 0.1

        topics = topics or cls.IMPORTANT_TOPICS
        content_lower = content.lower()
        score = 0.3  # base score / 基础分

        # Check each important topic / 检查每个重要主题
        for topic in topics:
            if topic.lower() in content_lower:
                score += 0.15

        # Longer content may contain more information / 较长的内容可能包含更多信息
        word_count = len(content.split())
        if word_count > 50:
            score += 0.1
        if word_count > 200:
            score += 0.1

        # Presence of structured data indicators / 结构化数据指示符
        if re.search(r'\b(user|name|id|key|token|url|email|phone)\b', content_lower):
            score += 0.1

        return min(score, 1.0)

    @classmethod
    def score_recency(cls, created_at: float, now: Optional[float] = None) -> float:
        """
        Score based on recency. Newer memories get a boost.
        根据时间接近度评分。越新的记忆得分越高。

        Uses exponential decay: boost = e^(-days/30)
        使用指数衰减：boost = e^(-天数/30)

        Returns a multiplier in (0, 1].
        """
        now = now or time.time()
        age_seconds = now - created_at
        if age_seconds <= 0:
            return 1.0
        days = age_seconds / 86400.0
        return max(0.1, pow(2.718, -days / 30.0))

    @classmethod
    def score_frequency(cls, access_count: int) -> float:
        """
        Score based on access frequency.
        根据访问频率评分。

        Returns a multiplier in [1.0, 2.0].
        """
        if access_count <= 0:
            return 1.0
        # Diminishing returns / 边际递减: log2(access_count + 1) + 1
        import math
        return min(2.0, 1.0 + math.log2(access_count + 1) * 0.15)

    @classmethod
    def combined_score(
        cls,
        content: str,
        created_at: float,
        access_count: int = 0,
        topics: Optional[list[str]] = None,
        now: Optional[float] = None,
    ) -> float:
        """
        Calculate combined importance score (0-1).
        计算综合重要性评分 (0-1)。

        Formula:
            score = content_score * 0.5 + recency_mult * 0.3 + freq_mult * 0.2
        """
        cs = cls.score_content(content, topics)
        rm = cls.score_recency(created_at, now)
        fm = cls.score_frequency(access_count)

        combined = cs * 0.5 + rm * 0.3 + fm * 0.2
        return min(combined, 1.0)


# ---------------------------------------------------------------------------
# PruningStrategy — 自动记忆管理
# ---------------------------------------------------------------------------

class PruningStrategy:
    """
    Automatic memory management — removes low-importance and expired memories.
    自动记忆管理 — 移除低重要性和过期的记忆。
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def prune(self, keep_top_k: int = 1000) -> int:
        """
        Remove lowest-importance memories, keeping only top K.
        移除重要性最低的记忆，仅保留前 K 条。

        Also removes expired TTL memories first.
        同时会先移除已过 TTL 的记忆。

        Returns:
            删除条数 / number of deleted memories
        """
        deleted = 0

        # Step 1: remove expired TTL / 第一步：清除过期 TTL
        deleted += self.ttl_expired()

        with self.store._lock:
            cur = self.store._conn.cursor()

            # Count total / 统计总数
            cur.execute("SELECT COUNT(*) as cnt FROM memories")
            total = cur.fetchone()["cnt"]

            if total <= keep_top_k:
                return deleted  # nothing to prune / 无需裁剪

            # Find IDs of memories to delete (oldest + lowest importance beyond top K)
            # 找出需要删除的记忆 ID（超出前 K 条中，最旧且重要性最低的）
            to_delete = total - keep_top_k
            cur.execute(
                """SELECT id FROM memories
                   ORDER BY importance ASC, created_at ASC
                   LIMIT ?""",
                (to_delete,),
            )
            ids_to_delete = [row["id"] for row in cur.fetchall()]

            if ids_to_delete:
                placeholders = ",".join("?" for _ in ids_to_delete)
                cur.execute(
                    f"DELETE FROM memories WHERE id IN ({placeholders})",
                    ids_to_delete,
                )
                deleted += cur.rowcount
                self.store._conn.commit()

        return deleted

    def ttl_expired(self) -> int:
        """
        Remove memories whose TTL has expired.
        删除已过 TTL 的记忆。

        Returns:
            删除条数 / number of deleted memories
        """
        now = time.time()
        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute("DELETE FROM memories WHERE ttl IS NOT NULL AND ttl < ?", (now,))
            deleted = cur.rowcount
            self.store._conn.commit()
        return deleted

    def get_stats(self) -> dict:
        """
        Get pruning-related statistics.
        获取与裁剪相关的统计信息。

        Returns:
            dict with: total, expired_ttl_count, importance_distribution
        """
        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM memories")
            total = cur.fetchone()["cnt"]

            cur.execute(
                "SELECT COUNT(*) as cnt FROM memories WHERE ttl IS NOT NULL AND ttl < ?",
                (time.time(),),
            )
            expired = cur.fetchone()["cnt"]

            cur.execute("""
                SELECT
                    SUM(CASE WHEN importance >= 0.8 THEN 1 ELSE 0 END) as high,
                    SUM(CASE WHEN importance >= 0.5 AND importance < 0.8 THEN 1 ELSE 0 END) as medium,
                    SUM(CASE WHEN importance < 0.5 THEN 1 ELSE 0 END) as low
                FROM memories
            """)
            dist = dict(cur.fetchone())

        return {
            "total": total,
            "expired_ttl_count": expired,
            "importance_distribution": dist,
        }


# ---------------------------------------------------------------------------
# ContextInjector — 为 LLM 上下文准备记忆
# ---------------------------------------------------------------------------

class ContextInjector:
    """
    Prepare memories for injection into LLM context.
    将记忆处理成适合注入 LLM 上下文的格式。

    The output is a formatted string with clear section markers,
    designed to be appended to the system prompt or conversation history.
    """

    # 上下文的最大 token 估算（按每 token ~4 字符估算）
    # Rough estimate: ~4 chars per token
    CHARS_PER_TOKEN = 4

    def __init__(self, store: MemoryStore):
        self.store = store

    def get_relevant_context(self, query: str, max_tokens: int = 2000) -> str:
        """
        Get formatted memory context for LLM injection.
        获取格式化的记忆上下文，用于注入 LLM。

        Args:
            query: 当前查询或主题 / current query or topic
            max_tokens: 最大 token 预算 / max token budget

        Returns:
            Formatted string ready to append to system prompt.
            格式化字符串，可直接追加到系统提示中。
        """
        max_chars = max_tokens * self.CHARS_PER_TOKEN

        # Retrieve relevant memories / 检索相关记忆
        memories = self.store.recall(query, limit=20)

        if not memories:
            return ""

        # Build formatted sections / 构建格式化章节
        sections = []
        chars_used = 0

        # Group by type for better readability / 按类型分组以便阅读
        by_type: dict[str, list[dict]] = {}
        for m in memories:
            t = m.get("type", "other")
            by_type.setdefault(t, []).append(m)

        # Sort type groups by average importance / 按平均重要性排序类型组
        type_order = sorted(
            by_type.keys(),
            key=lambda t: sum(m["importance"] for m in by_type[t]) / len(by_type[t]),
            reverse=True,
        )

        header = "<atlas_memory_context>\n"
        footer = "\n</atlas_memory_context>"
        chars_used += len(header) + len(footer)

        for mtype in type_order:
            if chars_used >= max_chars:
                break

            section_header = f"\n  <!-- {mtype} memories -->\n"
            chars_used += len(section_header)
            if chars_used > max_chars:
                break

            items = []
            for mem in by_type[mtype]:
                entry = (
                    f"    [{mem['key']}] "
                    f"(importance={mem['importance']:.2f}) "
                    f"{mem['content']}"
                )
                entry_chars = len(entry) + 1  # +1 for newline
                if chars_used + entry_chars > max_chars:
                    break  # budget exhausted / 预算耗尽
                items.append(entry)
                chars_used += entry_chars

            if items:
                sections.append(section_header + "\n".join(items))

        if not sections:
            return ""

        return header + "".join(sections) + footer

    def get_formatted_context(self, query: str, max_tokens: int = 2000) -> str:
        """
        Alias for get_relevant_context. / get_relevant_context 的别名。
        """
        return self.get_relevant_context(query, max_tokens)


# ---------------------------------------------------------------------------
# 便捷工厂函数 / convenience factory
# ---------------------------------------------------------------------------

def create_memory_engine(db_path: str = DEFAULT_DB_PATH) -> tuple:
    """
    Create a fully configured memory engine with all components.
    创建完整配置的记忆引擎，包含所有组件。

    Returns:
        (MemoryStore, ImportanceScorer, PruningStrategy, ContextInjector)
    """
    store = MemoryStore(db_path)
    scorer = ImportanceScorer()
    pruner = PruningStrategy(store)
    injector = ContextInjector(store)
    return store, scorer, pruner, injector
