#!/usr/bin/env python3
"""
Atlas Memory Engine — 记忆引擎
=================================

持久记忆存储 (SQLite) / 重要性评分 / 自动裁剪 / 上下文注入 / 导入导出

Uses only Python stdlib — no external dependencies.
完全使用 Python 标准库，无外部依赖。
"""

import difflib
import json
import math
import os
import re
import shutil
import sqlite3
import threading
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Reuse the MemoryEntry dataclass from architecture for compatibility
# 复用 architecture 中定义的 MemoryEntry 以保证兼容
from atlas_core.architecture import MemoryEntry

# Optional sentence-transformers for vector search
# 可选依赖，导入失败时回退
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None


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
                    related_ids TEXT NOT NULL DEFAULT '[]',
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

                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    memory_id INTEGER PRIMARY KEY,
                    embedding BLOB,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
                );
            """)

            # Backward-compatible migration: add related_ids column if it doesn't exist
            # 向后兼容迁移：如果 related_ids 列不存在则添加
            try:
                cur.execute("ALTER TABLE memories ADD COLUMN related_ids TEXT NOT NULL DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass  # column already exists / 列已存在

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
        related_ids: Optional[list[int]] = None,
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
            related_ids: 关联记忆 ID 列表 / list of related memory IDs

        Returns:
            memory_id: 新记忆的 ID / the new memory's ID
        """
        if importance is None:
            importance = ImportanceScorer.score_content(content)

        tags = tags or []
        related_ids = related_ids or []
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
                    """INSERT INTO memories (key, content, type, tags, related_ids, importance,
                       created_at, updated_at, access_count, ttl)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (key, content, type, json.dumps(tags), json.dumps(related_ids),
                     importance, now, now, ttl_expire),
                )
                memory_id = cur.lastrowid

            # Update tags table / 更新标签表
            cur.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
            for tag in tags:
                cur.execute(
                    "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory_id, tag),
                )

            # Update related_ids if provided and memory already existed
            # 如果提供了 related_ids 且记忆已存在，更新关联
            if row and related_ids:
                cur.execute(
                    "UPDATE memories SET related_ids = ? WHERE id = ?",
                    (json.dumps(related_ids), memory_id),
                )

            self._conn.commit()

        # Post-save: auto-generate embedding / 保存后自动生成向量
        try:
            if _HAS_SENTENCE_TRANSFORMERS:
                VectorSearch(self)._store_embedding(memory_id, content)
        except Exception:
            warnings.warn("Vector auto-embedding failed, skipping")

        # Post-save: auto-detect similar memories and link them
        # 保存后自动检测高相似度记忆并建立关联
        try:
            self._auto_link_memory(memory_id, content)
        except Exception:
            warnings.warn("Auto-linking failed, skipping")

        return memory_id

    def _auto_link_memory(self, memory_id: int, content: str):
        """Auto-link newly saved memory with existing highly similar memories.
        自动将新保存的记忆与已有的高相似度记忆建立关联。"""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT id, content FROM memories WHERE id != ?",
                (memory_id,),
            )
            existing = cur.fetchall()

        linked = set()
        for row in existing:
            other_id = row["id"]
            other_content = row["content"]
            ratio = difflib.SequenceMatcher(None, content, other_content).ratio()
            if ratio > 0.8:
                self.link_memories(memory_id, other_id)
                linked.add(other_id)

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
                d["related_ids"] = json.loads(d["related_ids"]) if isinstance(d.get("related_ids"), str) else (d.get("related_ids") or [])
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
            d["related_ids"] = json.loads(d["related_ids"]) if isinstance(d.get("related_ids"), str) else (d.get("related_ids") or [])
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
                if isinstance(r.get("related_ids"), str):
                    r["related_ids"] = json.loads(r["related_ids"])

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
    # 记忆图谱 / memory graph
    # -----------------------------------------------------------------------

    def link_memories(self, id1: int, id2: int) -> bool:
        """
        Create a bidirectional link between two memories.
        在两个记忆之间建立双向关联。

        Args:
            id1: 第一个记忆 ID / first memory ID
            id2: 第二个记忆 ID / second memory ID

        Returns:
            True if successful, False if either memory doesn't exist.
        """
        if id1 == id2:
            return False
        with self._lock:
            cur = self._conn.cursor()
            # Verify both exist / 验证两者都存在
            cur.execute("SELECT id FROM memories WHERE id IN (?, ?)", (id1, id2))
            found = {row["id"] for row in cur.fetchall()}
            if id1 not in found or id2 not in found:
                return False

            # Update id1's related_ids / 更新 id1 的关联列表
            cur.execute("SELECT related_ids FROM memories WHERE id = ?", (id1,))
            ids1 = json.loads(cur.fetchone()["related_ids"])
            if id2 not in ids1:
                ids1.append(id2)
                cur.execute(
                    "UPDATE memories SET related_ids = ? WHERE id = ?",
                    (json.dumps(ids1), id1),
                )

            # Update id2's related_ids / 更新 id2 的关联列表
            cur.execute("SELECT related_ids FROM memories WHERE id = ?", (id2,))
            ids2 = json.loads(cur.fetchone()["related_ids"])
            if id1 not in ids2:
                ids2.append(id1)
                cur.execute(
                    "UPDATE memories SET related_ids = ? WHERE id = ?",
                    (json.dumps(ids2), id2),
                )

            self._conn.commit()
        return True

    def unlink_memories(self, id1: int, id2: int) -> bool:
        """
        Remove a bidirectional link between two memories.
        取消两个记忆之间的双向关联。

        Args:
            id1: 第一个记忆 ID / first memory ID
            id2: 第二个记忆 ID / second memory ID

        Returns:
            True if successful, False if either memory doesn't exist.
        """
        if id1 == id2:
            return False
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT id FROM memories WHERE id IN (?, ?)", (id1, id2))
            found = {row["id"] for row in cur.fetchall()}
            if id1 not in found or id2 not in found:
                return False

            # Update id1's related_ids / 更新 id1 的关联列表
            cur.execute("SELECT related_ids FROM memories WHERE id = ?", (id1,))
            ids1 = json.loads(cur.fetchone()["related_ids"])
            if id2 in ids1:
                ids1.remove(id2)
                cur.execute(
                    "UPDATE memories SET related_ids = ? WHERE id = ?",
                    (json.dumps(ids1), id1),
                )

            # Update id2's related_ids / 更新 id2 的关联列表
            cur.execute("SELECT related_ids FROM memories WHERE id = ?", (id2,))
            ids2 = json.loads(cur.fetchone()["related_ids"])
            if id1 in ids2:
                ids2.remove(id1)
                cur.execute(
                    "UPDATE memories SET related_ids = ? WHERE id = ?",
                    (json.dumps(ids2), id2),
                )

            self._conn.commit()
        return True

    def get_memory_graph(self, memory_id: int, depth: int = 2) -> dict:
        """
        Recursively retrieve the association network of a memory.
        递归获取记忆的关联网络。

        Args:
            memory_id: 起始记忆 ID / starting memory ID
            depth: 递归深度 / recursion depth

        Returns:
            dict of {id: {content, type, importance, related: [...]}}
        """
        graph = {}
        visited = set()

        def _traverse(mid: int, remaining_depth: int):
            if mid in visited or remaining_depth < 0:
                return
            visited.add(mid)

            with self._lock:
                cur = self._conn.cursor()
                cur.execute("SELECT * FROM memories WHERE id = ?", (mid,))
                row = cur.fetchone()
                if row is None:
                    return
                d = dict(row)
                d["tags"] = json.loads(d["tags"]) if isinstance(d.get("tags"), str) else (d.get("tags") or [])
                related = json.loads(d["related_ids"]) if isinstance(d.get("related_ids"), str) else (d.get("related_ids") or [])
                d["related_ids"] = related

            graph[mid] = {
                "content": d["content"],
                "type": d["type"],
                "importance": d["importance"],
                "related": related,
            }

            if remaining_depth > 0:
                for rel_id in related:
                    _traverse(rel_id, remaining_depth - 1)

        _traverse(memory_id, depth)
        return graph

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

    def decay(self, decay_rate: float = 0.1, max_age_days: int = 30) -> int:
        """
        Reduce importance of long-unaccessed low-importance memories.
        降低长时间未访问的低重要性记忆的重要性。

        Formula: new_imp = imp * (1 - decay_rate * days_since_last_access / 30)
        Only affects memories with access_count=0 or importance < 0.5.
        Floor at 0.05.

        Args:
            decay_rate: 衰减率 / decay rate (default 0.1)
            max_age_days: 最大天数阈值 / max age threshold (default 30)

        Returns:
            受影响的数量 / number of affected memories
        """
        now = time.time()
        affected = 0
        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute(
                """SELECT id, importance, updated_at, access_count
                   FROM memories
                   WHERE access_count = 0 OR importance < 0.5"""
            )
            rows = cur.fetchall()

            for row in rows:
                mid = row["id"]
                imp = row["importance"]
                updated_at = row["updated_at"]
                access_count = row["access_count"]

                days_since = (now - updated_at) / 86400.0
                if days_since <= 0:
                    continue

                # Apply decay formula / 应用衰减公式
                new_imp = imp * (1 - decay_rate * min(days_since, max_age_days) / max_age_days)
                new_imp = max(0.05, new_imp)  # floor at 0.05 / 下限 0.05

                if new_imp < imp:
                    cur.execute(
                        "UPDATE memories SET importance = ? WHERE id = ?",
                        (new_imp, mid),
                    )
                    affected += 1

            self.store._conn.commit()

        return affected


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
# VectorSearch — 向量搜索（可选依赖）
# ---------------------------------------------------------------------------

class VectorSearch:
    """
    Vector-based semantic search using sentence-transformers.
    基于向量的语义搜索，使用 sentence-transformers。

    Optional dependency — falls back gracefully if sentence-transformers is not installed.
    可选依赖 — 如果未安装 sentence-transformers 则优雅回退。
    """

    _model = None
    _model_name = "all-MiniLM-L6-v2"

    @classmethod
    def _get_model(cls):
        """Lazy-load the sentence transformer model.
        延迟加载 sentence transformer 模型。"""
        if cls._model is None and _HAS_SENTENCE_TRANSFORMERS:
            try:
                cls._model = SentenceTransformer(cls._model_name)
            except Exception as e:
                warnings.warn(f"Failed to load sentence-transformers model: {e}")
                return None
        return cls._model

    def __init__(self, store: MemoryStore):
        self.store = store

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """
        Pure Python cosine similarity between two vectors.
        纯 Python 实现的两个向量之间的余弦相似度。
        """
        dot = sum(ax * bx for ax, bx in zip(a, b))
        norm_a = sum(ax * ax for ax in a) ** 0.5
        norm_b = sum(bx * bx for bx in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _store_embedding(self, memory_id: int, content: str):
        """
        Compute and store embedding for a memory.
        计算并存储记忆的向量。

        Silently fails if model is not available.
        如果模型不可用则静默失败。
        """
        model = self._get_model()
        if model is None:
            return

        try:
            embedding = model.encode(content).tolist()
            embedding_blob = json.dumps(embedding)
            now = time.time()
            with self.store._lock:
                cur = self.store._conn.cursor()
                cur.execute(
                    """INSERT OR REPLACE INTO memory_embeddings
                       (memory_id, embedding, updated_at)
                       VALUES (?, ?, ?)""",
                    (memory_id, embedding_blob, now),
                )
                self.store._conn.commit()
        except Exception as e:
            warnings.warn(f"Failed to store embedding for memory {memory_id}: {e}")

    def search(self, query: str, limit: int = 10) -> list[tuple[int, float]]:
        """
        Search memories by vector similarity to the query.
        按向量相似度搜索记忆。

        Args:
            query: 查询文本 / query text
            limit: 最大结果数 / max results

        Returns:
            list of (memory_id, score) tuples sorted by descending similarity.
            Returns empty list if sentence-transformers is not available.
        """
        model = self._get_model()
        if model is None:
            warnings.warn(
                "Vector search requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )
            return []

        try:
            query_embedding = model.encode(query).tolist()
        except Exception as e:
            warnings.warn(f"Failed to encode query: {e}")
            return []

        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute(
                "SELECT memory_id, embedding FROM memory_embeddings WHERE embedding IS NOT NULL"
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            mid = row["memory_id"]
            try:
                stored_emb = json.loads(row["embedding"])
                score = self._cosine_similarity(query_embedding, stored_emb)
                results.append((mid, score))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        # Sort by score descending and return top-k / 按分数降序排列，返回前 k 条
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


# ---------------------------------------------------------------------------
# MemoryConsolidator — 记忆合并去重
# ---------------------------------------------------------------------------

class MemoryConsolidator:
    """
    Detects and merges duplicate or highly similar memories.
    检测并合并重复或高度相似的记忆。
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def consolidate(self, similarity_threshold: float = 0.85) -> dict:
        """
        Scan all memory pairs and merge highly similar ones.
        扫描所有记忆对并合并高度相似的记忆。

        Merge strategy: keep the one with higher importance,
        merge tags (deduplicated), append content.

        Args:
            similarity_threshold: 相似度阈值 / similarity threshold (default 0.85)

        Returns:
            dict with merged_count and deleted_count
        """
        merged = 0
        deleted = 0

        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute("SELECT id, content, importance, tags FROM memories ORDER BY id")
            all_memories = cur.fetchall()

        # Compare all pairs / 比较所有对
        for i in range(len(all_memories)):
            if all_memories[i] is None:
                continue
            for j in range(i + 1, len(all_memories)):
                if all_memories[j] is None:
                    continue

                m1 = all_memories[i]
                m2 = all_memories[j]

                id1, content1, imp1, tags1_raw = m1["id"], m1["content"], m1["importance"], m1["tags"]
                id2, content2, imp2, tags2_raw = m2["id"], m2["content"], m2["importance"], m2["tags"]

                ratio = difflib.SequenceMatcher(None, content1, content2).ratio()
                if ratio < similarity_threshold:
                    continue

                # Decide which to keep (higher importance) / 决定保留哪个（高重要性）
                if imp1 >= imp2:
                    keep_id, keep_content, keep_imp, keep_tags_raw = id1, content1, imp1, tags1_raw
                    remove_id, remove_content, remove_tags_raw = id2, content2, tags2_raw
                    remove_idx = j
                else:
                    keep_id, keep_content, keep_imp, keep_tags_raw = id2, content2, imp2, tags2_raw
                    remove_id, remove_content, remove_tags_raw = id1, content1, tags1_raw
                    remove_idx = i

                # Merge tags / 合并标签（去重）
                try:
                    keep_tags = set(json.loads(keep_tags_raw) if isinstance(keep_tags_raw, str) else (keep_tags_raw or []))
                except (json.JSONDecodeError, TypeError):
                    keep_tags = set()
                try:
                    remove_tags = set(json.loads(remove_tags_raw) if isinstance(remove_tags_raw, str) else (remove_tags_raw or []))
                except (json.JSONDecodeError, TypeError):
                    remove_tags = set()
                merged_tags = list(keep_tags | remove_tags)

                # Append content if not already contained / 如果未包含则追加内容
                if remove_content not in keep_content:
                    merged_content = keep_content + "\n---\n" + remove_content
                else:
                    merged_content = keep_content

                # Update the kept memory / 更新保留的记忆
                with self.store._lock:
                    c = self.store._conn.cursor()
                    c.execute(
                        """UPDATE memories SET content=?, tags=?, importance=?, updated_at=?
                           WHERE id=?""",
                        (merged_content, json.dumps(merged_tags), keep_imp, time.time(), keep_id),
                    )
                    # Delete the redundant memory / 删除冗余记忆
                    c.execute("DELETE FROM memories WHERE id = ?", (remove_id,))
                    self.store._conn.commit()

                # Mark as removed in our local list / 在本地列表中标记为已删除
                all_memories[remove_idx] = None

                merged += 1
                deleted += 1

                # If we removed the outer-loop item, skip remaining inner loop
                # 如果删除了外层循环项，跳过剩余内层循环
                if remove_idx == i:
                    break

        return {"merged_count": merged, "deleted_count": deleted}

    def get_stats(self) -> dict:
        """
        Get statistics about potential duplicates.
        获取关于潜在重复的统计信息。

        Returns:
            dict with total, potential_duplicates, avg_similarity
        """
        with self.store._lock:
            cur = self.store._conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM memories")
            total = cur.fetchone()["cnt"]

            cur.execute("SELECT id, content FROM memories ORDER BY id")
            all_memories = cur.fetchall()

        if total < 2:
            return {"total": total, "potential_duplicates": 0, "avg_similarity": 0.0}

        # Sample up to 200 pairs for performance / 最多采样 200 对以保证性能
        pair_count = 0
        total_similarity = 0.0
        duplicate_count = 0
        max_pairs = min(200, total * (total - 1) // 2)

        for i in range(len(all_memories)):
            for j in range(i + 1, len(all_memories)):
                if pair_count >= max_pairs:
                    break
                ratio = difflib.SequenceMatcher(
                    None, all_memories[i]["content"], all_memories[j]["content"]
                ).ratio()
                total_similarity += ratio
                pair_count += 1
                if ratio > 0.85:
                    duplicate_count += 1
            if pair_count >= max_pairs:
                break

        avg_sim = total_similarity / pair_count if pair_count > 0 else 0.0
        return {
            "total": total,
            "potential_duplicates": duplicate_count,
            "avg_similarity": round(avg_sim, 4),
        }


# ---------------------------------------------------------------------------
# 便捷工厂函数 / convenience factory
# ---------------------------------------------------------------------------

class MemoryEngine:
    """
    Container for all memory engine components.
    所有记忆引擎组件的容器。

    Supports unpacking as (store, scorer, pruner, injector) for backward compatibility.
    支持解包为 (store, scorer, pruner, injector) 以保持向后兼容。
    """

    def __init__(self, store, scorer, pruner, injector, vector_search, consolidator):
        self.store = store
        self.scorer = scorer
        self.pruner = pruner
        self.injector = injector
        self.vector_search = vector_search
        self.consolidator = consolidator
        self._components = (store, scorer, pruner, injector)

    def __iter__(self):
        return iter(self._components)

    def __len__(self):
        return 4

    def __getitem__(self, idx):
        return self._components[idx]


def create_memory_engine(db_path: str = DEFAULT_DB_PATH) -> MemoryEngine:
    """
    Create a fully configured memory engine with all components.
    创建完整配置的记忆引擎，包含所有组件。

    Returns:
        MemoryEngine object with attributes: store, scorer, pruner, injector,
        vector_search, consolidator.
        Also unpackable as (store, scorer, pruner, injector) for backward compatibility.
    """
    store = MemoryStore(db_path)
    scorer = ImportanceScorer()
    pruner = PruningStrategy(store)
    injector = ContextInjector(store)
    vector_search = VectorSearch(store)
    consolidator = MemoryConsolidator(store)
    return MemoryEngine(
        store=store,
        scorer=scorer,
        pruner=pruner,
        injector=injector,
        vector_search=vector_search,
        consolidator=consolidator,
    )
