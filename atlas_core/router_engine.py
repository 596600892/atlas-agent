#!/usr/bin/env python3
"""
Atlas Router Engine — 分层意图路由引擎 v2
===========================================
Phase 5: Hierarchical routing, multi-intent decomposition,
         LLM-enhanced classification, fallback chains, result aggregation.

分层路由、多意图分解、LLM辅助分类、回退链、结果聚合。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from atlas_core.architecture import (
    AgentCapability as ArchCapability,
    ArchComponent,
    ComponentRegistry,
)


# ══════════════════════════════════════════════════════════════
# 增强枚举 / Enhanced enums
# ══════════════════════════════════════════════════════════════


class RouteLevel(Enum):
    """路由层次 / Route hierarchy level."""
    DOMAIN = "domain"        # 顶层领域 / Top-level domain
    SUB_DOMAIN = "sub"       # 子领域 / Sub-domain
    AGENT = "agent"          # 具体Agent / Specific agent


class ConfidenceLevel(Enum):
    """置信度等级 / Confidence quantiles."""
    HIGH = "high"           # > 0.6
    MEDIUM = "medium"       # > 0.3
    LOW = "low"             # > 0.0
    UNKNOWN = "unknown"     # = 0.0


class FallbackStrategy(Enum):
    """回退策略 / Fallback strategies."""
    STRICT = "strict"        # 只精确匹配 / Exact match only
    RELAXED = "relaxed"      # 降低阈值 / Lower threshold
    CASCADE = "cascade"      # 逐级回退到低一级 / Cascade down one level


class AggregationStrategy(Enum):
    """结果聚合策略 / Result aggregation strategies."""
    FIRST_MATCH = "first"    # 只取最高分 / Only highest score
    WEIGHTED = "weighted"    # 加权合并 / Weighted combination
    MERGE = "merge"          # 合并所有意图 / Merge all intents
    PARALLEL = "parallel"    # 并行分派所有匹配Agent / Dispatch all matched agents


# ══════════════════════════════════════════════════════════════
# 向后兼容 — 保持原有枚举值可用
# ══════════════════════════════════════════════════════════════

AgentCapability = ArchCapability


# ══════════════════════════════════════════════════════════════
# AgentManifest (向后兼容)
# ══════════════════════════════════════════════════════════════


@dataclass
class AgentManifest:
    """Agent 注册清单 / Agent registration manifest."""
    name: str
    repo_url: str
    capabilities: list[AgentCapability]
    description: str
    pip_package: str = ""


# ══════════════════════════════════════════════════════════════
# 路由结果类型 / Route result types
# ══════════════════════════════════════════════════════════════


@dataclass
class IntentResult:
    """意图路由结果 / Intent routing result."""
    query: str
    primary_intent: Optional[AgentCapability] = None
    confidence: float = 0.0
    matched_agents: list[tuple[str, float]] = field(default_factory=list)
    suggested_command: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    fallback_used: bool = False
    sub_intents: list[dict] = field(default_factory=list)


@dataclass
class RoutingPlan:
    """完整路由计划 / Full routing plan (multi-intent support)."""
    query: str
    level: RouteLevel
    strategy: AggregationStrategy
    decisions: list[IntentResult] = field(default_factory=list)
    aggregate_confidence: float = 0.0

    @property
    def primary_agent(self) -> Optional[str]:
        """获取首要Agent名称 / Get primary agent name."""
        if not self.decisions:
            return None
        return self.decisions[0].primary_intent.value if self.decisions[0].primary_intent else None


# ══════════════════════════════════════════════════════════════
# 14 Agent 注册表
# ══════════════════════════════════════════════════════════════

REGISTRY: dict[str, AgentManifest] = {
    "finance-agent": AgentManifest(
        name="finance-agent",
        repo_url="https://github.com/596600892/finance-agent",
        capabilities=[AgentCapability.FINANCE_PREDICTION],
        description="8D stock prediction, factor analysis, portfolio",
        pip_package="finance-agent",
    ),
    "screenplay-agent": AgentManifest(
        name="screenplay-agent",
        repo_url="https://github.com/596600892/screenplay-agent",
        capabilities=[AgentCapability.SCREENPLAY_WRITING],
        description="Screenplay writing, character development, plot",
        pip_package="screenplay-agent",
    ),
    "image-gen-agent": AgentManifest(
        name="image-gen-agent",
        repo_url="https://github.com/596600892/image-agent",
        capabilities=[AgentCapability.IMAGE_GENERATION],
        description="Text-to-image, style transfer, image editing",
        pip_package="image-gen-agent",
    ),
    "video-prod-agent": AgentManifest(
        name="video-prod-agent",
        repo_url="https://github.com/596600892/video-agent",
        capabilities=[AgentCapability.VIDEO_PRODUCTION],
        description="Video generation, editing, subtitles, effects",
        pip_package="video-prod-agent",
    ),
    "market-monitor-agent": AgentManifest(
        name="market-monitor-agent",
        repo_url="https://github.com/596600892/market-monitor",
        capabilities=[AgentCapability.MARKET_MONITORING],
        description="Market monitoring, trend ID, risk alerts",
        pip_package="market-monitor-agent",
    ),
    "cross-domain-learner": AgentManifest(
        name="cross-domain-learner",
        repo_url="https://github.com/596600892/cross-domain-learner",
        capabilities=[AgentCapability.CROSS_DOMAIN_LEARNING],
        description="Cross-domain transfer, idle-learning loop",
        pip_package="cross-domain-learner",
    ),
    "ecommerce-agent": AgentManifest(
        name="ecommerce-agent",
        repo_url="https://github.com/596600892/ecommerce-agent",
        capabilities=[AgentCapability.ECOMMERCE_OPS],
        description="E-commerce automation, product, order management",
        pip_package="ecommerce-agent",
    ),
    "short-video-agent": AgentManifest(
        name="short-video-agent",
        repo_url="https://github.com/596600892/short-video-ops-agent",
        capabilities=[AgentCapability.SHORT_VIDEO_OPS],
        description="Short video strategy, content optimization",
        pip_package="short-video-agent",
    ),
    "swarm-sim-agent": AgentManifest(
        name="swarm-sim-agent",
        repo_url="https://github.com/596600892/mirofish-simulator",
        capabilities=[AgentCapability.SWARM_SIMULATION],
        description="Swarm simulation, prediction aggregation",
        pip_package="swarm-sim-agent",
    ),
    "system-sentinel": AgentManifest(
        name="system-sentinel",
        repo_url="https://github.com/596600892/system-sentinel",
        capabilities=[AgentCapability.SYSTEM_MONITORING],
        description="Health monitoring, resource management",
        pip_package="system-sentinel",
    ),
    "fault-analysis-agent": AgentManifest(
        name="fault-analysis-agent",
        repo_url="https://github.com/596600892/deerflow-orchestrator",
        capabilities=[AgentCapability.FAULT_ANALYSIS],
        description="Fault diagnosis, root cause analysis",
        pip_package="fault-analysis-agent",
    ),
    "token-budget-agent": AgentManifest(
        name="token-budget-agent",
        repo_url="https://github.com/596600892/token-budget-agent",
        capabilities=[AgentCapability.TOKEN_MANAGEMENT],
        description="Token budget, cost optimization, quota",
        pip_package="token-budget-agent",
    ),
    "creative-coordinator": AgentManifest(
        name="creative-coordinator",
        repo_url="https://github.com/596600892/creative-coordinator",
        capabilities=[AgentCapability.CREATIVE_COORDINATION],
        description="Creative project orchestration, multi-modal",
        pip_package="creative-coordinator",
    ),
    "task-orchestrator": AgentManifest(
        name="task-orchestrator",
        repo_url="https://github.com/596600892/ceo-agent-orchestrator",
        capabilities=[AgentCapability.TASK_ORCHESTRATION],
        description="Multi-agent task orchestration, workflows",
        pip_package="task-orchestrator",
    ),
}


# ══════════════════════════════════════════════════════════════
# 关键词模式定义
# ══════════════════════════════════════════════════════════════

# 顶层领域映射 / Top-level domain groups
_DOMAIN_GROUPS: dict[str, list[AgentCapability]] = {
    "finance": [
        AgentCapability.FINANCE_PREDICTION,
        AgentCapability.MARKET_MONITORING,
    ],
    "creative": [
        AgentCapability.SCREENPLAY_WRITING,
        AgentCapability.IMAGE_GENERATION,
        AgentCapability.VIDEO_PRODUCTION,
        AgentCapability.CREATIVE_COORDINATION,
        AgentCapability.SHORT_VIDEO_OPS,
        AgentCapability.ECOMMERCE_OPS,
    ],
    "tech": [
        AgentCapability.SYSTEM_MONITORING,
        AgentCapability.FAULT_ANALYSIS,
        AgentCapability.TOKEN_MANAGEMENT,
        AgentCapability.TASK_ORCHESTRATION,
    ],
    "learning": [
        AgentCapability.CROSS_DOMAIN_LEARNING,
        AgentCapability.SWARM_SIMULATION,
    ],
}

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "finance": [
        "stock", "price", "finance", "investment", "portfolio",
        "market", "trading", "earnings", "dividend", "股票", "股价",
        "投资", "金融", "行情", "理财",
    ],
    "creative": [
        "draw", "image", "video", "script", "screenplay", "create",
        "design", "art", "content", "product", "画", "图", "视频",
        "剧本", "创意", "设计", "电商", "商品",
    ],
    "tech": [
        "server", "system", "error", "fault", "monitor", "token",
        "task", "workflow", "pipeline", "系统", "服务器", "故障",
        "监控", "任务", "预算",
    ],
    "learning": [
        "learn", "study", "research", "swarm", "simulation",
        "knowledge", "insight", "学习", "研究", "群体", "模拟",
    ],
}

_INTENT_PATTERNS: dict[AgentCapability, dict[str, Any]] = {
    AgentCapability.FINANCE_PREDICTION: {
        "keywords": [
            "stock", "stocks", "price", "prices", "earnings", "finance",
            "financial", "investment", "invest", "portfolio", "dividend",
            "market cap", "ticker", "predict", "prediction", "forecast",
            "quote", "trading", "analysis", "股票", "股价", "金融",
            "投资", "理财", "基金", "收益率", "财报",
        ],
        "weight": 1.0,
    },
    AgentCapability.SCREENPLAY_WRITING: {
        "keywords": [
            "screenplay", "script", "scene", "dialogue", "plot",
            "character arc", "storyboard", "narrative", "剧本", "脚本",
            "台词", "情节", "角色", "叙事",
        ],
        "weight": 1.0,
    },
    AgentCapability.IMAGE_GENERATION: {
        "keywords": [
            "image", "picture", "photo", "generate", "draw",
            "illustration", "image generation", "text to image",
            "style transfer", "图像", "图片", "照片", "生成图片",
            "画图", "插图", "文生图", "风格迁移",
            "画", "图", "风景", "绘制", "构图", "画笔", "绘画",
        ],
        "weight": 1.0,
    },
    AgentCapability.VIDEO_PRODUCTION: {
        "keywords": [
            "video", "movie", "film", "animation", "edit", "produce",
            "video production", "video editing", "subtitle", "caption",
            "视频", "电影", "动画", "编辑视频", "制作视频", "字幕",
        ],
        "weight": 1.0,
    },
    AgentCapability.MARKET_MONITORING: {
        "keywords": [
            "market", "trend", "monitor", "surveillance", "alert",
            "risk", "market data", "real time", "quote",
            "市场", "行情", "监控", "趋势", "预警", "风险", "实时",
        ],
        "weight": 1.0,
    },
    AgentCapability.CROSS_DOMAIN_LEARNING: {
        "keywords": [
            "learn", "study", "knowledge", "cross domain", "transfer",
            "research", "insight", "discover",
            "学习", "研究", "知识", "跨领域", "迁移", "洞察", "发现",
        ],
        "weight": 0.8,
    },
    AgentCapability.ECOMMERCE_OPS: {
        "keywords": [
            "ecommerce", "e-commerce", "shop", "product", "inventory",
            "order", "listing", "fulfillment", "supplier",
            "电商", "商品", "订单", "库存", "店铺", "供应链",
        ],
        "weight": 1.0,
    },
    AgentCapability.SHORT_VIDEO_OPS: {
        "keywords": [
            "short video", "tiktok", "reels", "shorts", "viral",
            "content strategy", "engagement", "follower",
            "短视频", "抖音", "快手", "内容", "粉丝", "流量", "爆款",
        ],
        "weight": 1.0,
    },
    AgentCapability.SWARM_SIMULATION: {
        "keywords": [
            "swarm", "consensus", "collective", "simulation",
            "agent swarm", "multi agent", "prediction market",
            "群体", "群智", "共识", "模拟", "多智能体", "预测市场",
        ],
        "weight": 0.9,
    },
    AgentCapability.SYSTEM_MONITORING: {
        "keywords": [
            "system", "server", "health", "uptime", "monitoring",
            "resource", "cpu", "memory", "disk", "service",
            "系统", "服务器", "健康", "监控", "资源", "CPU", "内存",
        ],
        "weight": 1.0,
    },
    AgentCapability.FAULT_ANALYSIS: {
        "keywords": [
            "fault", "error", "bug", "crash", "failure", "diagnosis",
            "root cause", "debug", "exception",
            "故障", "错误", "崩溃", "异常", "诊断", "根因", "调试",
        ],
        "weight": 1.0,
    },
    AgentCapability.TOKEN_MANAGEMENT: {
        "keywords": [
            "token", "budget", "cost", "quota", "usage", "pricing",
            "token count", "limit", "rate limit",
            "Token", "预算", "成本", "配额", "用量", "计费", "限制",
        ],
        "weight": 0.9,
    },
    AgentCapability.CREATIVE_COORDINATION: {
        "keywords": [
            "creative", "art", "design", "project", "pipeline",
            "coordinate", "workflow", "collaboration",
            "创意", "艺术", "设计", "项目", "管线", "协作", "工作流",
        ],
        "weight": 0.8,
    },
    AgentCapability.TASK_ORCHESTRATION: {
        "keywords": [
            "task", "job", "workflow", "pipeline", "orchestrate",
            "automate", "schedule", "dependency",
            "任务", "工作流", "编排", "自动化", "调度", "依赖", "作业",
        ],
        "weight": 0.9,
    },
}


# ══════════════════════════════════════════════════════════════
# LLM增强分类器 / LLM-enhanced classifier (optional)
# ══════════════════════════════════════════════════════════════


class LLMEnhancer:
    """可选 LLM 增强分类器 / Optional LLM-enhanced intent classifier.

    When keyword confidence is below threshold, uses LLM to determine intent.
    Falls back to keyword-only if LLM is unavailable.
    """

    def __init__(self, api_url: str = "",
                 api_key: str = "", model: str = ""):
        self._api_url = api_url or os.environ.get("ATLAS_LLM_URL", "")
        self._api_key = api_key or os.environ.get("ATLAS_LLM_KEY", "")
        self._model = model or os.environ.get("ATLAS_LLM_MODEL", "default")
        self._available = bool(self._api_url)

    @property
    def available(self) -> bool:
        return self._available

    def classify(self, query: str,
                 candidates: list[AgentCapability]) -> dict[str, float]:
        """使用 LLM 为候选意图评分 / Score candidate intents using LLM.

        Args:
            query: 用户查询 / User query
            candidates: 候选能力列表 / Candidate capabilities

        Returns:
            dict: {capability_name: confidence_score}
        """
        if not self._available:
            return {}

        candidates_str = ", ".join(c.value for c in candidates)
        prompt = (
            f"Classify the following user query into one of these "
            f"intent categories: {candidates_str}\n"
            f"Query: {query}\n"
            f"Return only the category name and confidence (0-1) as JSON: "
            f'{{"intent": "category", "confidence": 0.0}}'
        )

        try:
            import urllib.request

            payload = json.dumps({
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }).encode("utf-8")

            headers = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            req = urllib.request.Request(
                self._api_url, data=payload, headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # 解析 LLM 返回 / Parse LLM response
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content)
            intent_name = parsed.get("intent", "")
            confidence = float(parsed.get("confidence", 0.5))

            # 匹配到对应能力 / Match to capability
            for cap in candidates:
                if cap.value == intent_name:
                    return {cap.value: min(confidence, 1.0)}

            return {}

        except Exception:
            return {}

    def classify_with_fallback(self, query: str,
                                candidates: list[AgentCapability],
                                keyword_scores: dict[AgentCapability, float],
                                threshold: float = 0.3) -> dict[AgentCapability, float]:
        """LLM+关键词混合分类 / Hybrid LLM+keyword classification.

        当关键词分数低于阈值时，调用 LLM 增强。
        """
        # 如果有高置信度的关键词匹配，直接返回
        high_conf = {k: v for k, v in keyword_scores.items() if v >= threshold}
        if high_conf:
            return high_conf

        # 关键词结果模糊 → 用LLM增强
        llm_raw = self.classify(query, candidates)
        # 转换LLM返回的字符串键为AgentCapability枚举
        llm_scores: dict[AgentCapability, float] = {}
        for cap_str, score in llm_raw.items():
            for cap in candidates:
                if cap.value == cap_str:
                    llm_scores[cap] = score
                    break

        if llm_scores:
            # 合并: LLM 分数 * 0.6 + 关键词分数 * 0.4
            merged = dict(keyword_scores)
            for cap, llm_score in llm_scores.items():
                kw_score = merged.get(cap, 0.0)
                merged[cap] = round(llm_score * 0.6 + kw_score * 0.4, 4)
            return merged

        return keyword_scores


# ══════════════════════════════════════════════════════════════
# IntentRouter — 分层意图路由核心
# ══════════════════════════════════════════════════════════════


class IntentRouter:
    """意图路由器 v2 / Intent Router v2

    Hierarchical routing with:
    - Multi-intent decomposition (compound queries like "draw stock chart")
    - Optional LLM-enhanced classification
    - Fallback chains (STRICT → RELAXED → CASCADE)
    - Configurable aggregation strategies
    """

    def __init__(self, registry: Optional[dict[str, AgentManifest]] = None,
                 llm_enhancer: Optional[LLMEnhancer] = None):
        self._registry = registry or REGISTRY
        self._patterns = _INTENT_PATTERNS
        self._domain_keywords = _DOMAIN_KEYWORDS
        self._domain_groups = _DOMAIN_GROUPS
        self._llm = llm_enhancer or LLMEnhancer()

    # ------------------------------------------------------------------
    # 核心路由方法 v2
    # ------------------------------------------------------------------

    def route(self, query: str,
              level: RouteLevel = RouteLevel.AGENT,
              strategy: FallbackStrategy = FallbackStrategy.STRICT,
              threshold: float = 0.0) -> list[tuple[AgentManifest, float]]:
        """对查询进行意图分类 / Classify intent of a query.

        Args:
            query: 用户输入的查询 / User query
            level: 路由层次 / Route hierarchy level
            strategy: 回退策略 / Fallback strategy
            threshold: 最低置信度阈值 / Minimum confidence threshold

        Returns:
            按置信度降序排列的 (AgentManifest, 置信度) 列表
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()

        # 1. 关键词评分
        score_map = self._score_all(query_lower)

        # 2. LLM增强（可选）
        if self._llm.available and max(score_map.values(), default=0.0) < 0.3:
            candidates = list(self._patterns.keys())
            llm_scores = self._llm.classify_with_fallback(
                query, candidates, score_map
            )
            score_map.update(llm_scores)

        # 3. 分层路由
        if level == RouteLevel.DOMAIN:
            return self._route_domain(query_lower, score_map, strategy, threshold)
        elif level == RouteLevel.SUB_DOMAIN:
            return self._route_domain(query_lower, score_map, strategy, threshold)

        # 4. 按Agent路由（默认）
        return self._route_agents(score_map, strategy, threshold)

    def analyze(self, query: str, **kwargs) -> IntentResult:
        """全面分析查询意图 / Full intent analysis."""
        matched = self.route(query, **kwargs)

        if not matched:
            return IntentResult(
                query=query,
                primary_intent=None,
                confidence=0.0,
                matched_agents=[],
                confidence_level=ConfidenceLevel.UNKNOWN,
            )

        primary_manifest, primary_conf = matched[0]
        primary_cap = primary_manifest.capabilities[0] if primary_manifest.capabilities else None
        matched_info = [(m.name, c) for m, c in matched]
        suggested = self._suggest_command(primary_cap, query)

        return IntentResult(
            query=query,
            primary_intent=primary_cap,
            confidence=primary_conf,
            matched_agents=matched_info,
            suggested_command=suggested,
            confidence_level=self._classify_confidence(primary_conf),
        )

    def decompose(self, query: str) -> list[IntentResult]:
        """将复合查询分解为多个子意图 /
        Decompose compound query into multiple sub-intents.

        E.g., "draw a stock chart of AAPL" → [IMAGE_GEN, FINANCE_PREDICTION]

        Args:
            query: 用户查询 / User query

        Returns:
            每个子意图的 IntentResult 列表
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        results: list[IntentResult] = []

        # 用关键词识别多个意图
        all_scores = self._score_all(query_lower)

        # 筛选出高于零分的意图
        active = {cap: score for cap, score in all_scores.items() if score > 0}
        if not active:
            return results

        # 按分数降序
        sorted_caps = sorted(active.items(), key=lambda x: x[1], reverse=True)

        for cap, score in sorted_caps:
            agents = self._find_agents_for_capability(cap, score)
            if agents:
                results.append(IntentResult(
                    query=query,
                    primary_intent=cap,
                    confidence=score,
                    matched_agents=[(a.name, score) for a, _ in agents],
                    confidence_level=self._classify_confidence(score),
                ))

        return results

    def plan(self, query: str,
             strategy: AggregationStrategy = AggregationStrategy.WEIGHTED,
             **route_kwargs) -> RoutingPlan:
        """制定完整路由计划 / Create a full routing plan.

        自动分解多意图，按聚合策略组合结果。
        """
        # 先尝试分解多意图 / Try decomposition first
        sub_intents = self.decompose(query)

        if not sub_intents:
            # 单意图回退 / Single intent fallback
            result = self.analyze(query, **route_kwargs)
            return RoutingPlan(
                query=query,
                level=route_kwargs.get("level", RouteLevel.AGENT),
                strategy=strategy,
                decisions=[result],
                aggregate_confidence=result.confidence,
            )

        # 聚合多意图结果
        if strategy == AggregationStrategy.FIRST_MATCH:
            agg_conf = sub_intents[0].confidence if sub_intents else 0.0
        elif strategy == AggregationStrategy.MERGE:
            # 合并所有置信度（上限1.0）
            agg_conf = min(sum(r.confidence for r in sub_intents), 1.0)
        else:
            # WEIGHTED: 主意图 0.6 + 辅助 0.4 / Primary 0.6 + secondary 0.4
            if len(sub_intents) >= 2:
                agg_conf = round(
                    sub_intents[0].confidence * 0.6
                    + sub_intents[1].confidence * 0.4, 4
                )
            else:
                agg_conf = sub_intents[0].confidence

        return RoutingPlan(
            query=query,
            level=route_kwargs.get("level", RouteLevel.AGENT),
            strategy=strategy,
            decisions=sub_intents,
            aggregate_confidence=min(agg_conf, 1.0),
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _score_all(self, query_lower: str) -> dict[AgentCapability, float]:
        """计算所有意图的关键词匹配分数 /
        Calculate keyword match scores for all intents."""
        scores: dict[AgentCapability, float] = {}
        for capability, pattern in self._patterns.items():
            score = self._score_intent(query_lower, pattern)
            if score > 0:
                scores[capability] = score
        return scores

    def _score_intent(self, query_lower: str, pattern: dict) -> float:
        """计算查询与模式的匹配分数 / Calculate match score."""
        keywords = pattern["keywords"]
        weight = pattern.get("weight", 1.0)
        words = query_lower.split()
        if not words:
            return 0.0

        matched_kw = sum(1 for kw in keywords if kw.lower() in query_lower)
        if matched_kw == 0:
            return 0.0

        raw = matched_kw / len(words)
        return round(min(raw, 1.0) * weight, 4)

    def _route_domain(self, query_lower: str,
                       score_map: dict[AgentCapability, float],
                       strategy: FallbackStrategy,
                       threshold: float) -> list[tuple[AgentManifest, float]]:
        """领域级路由 / Domain-level routing."""
        domain_scores: dict[str, float] = {}
        for domain, caps in self._domain_groups.items():
            domain_score = sum(score_map.get(c, 0.0) for c in caps)
            if domain_score > 0:
                domain_scores[domain] = domain_score

        if not domain_scores:
            return []

        best_domain = max(domain_scores, key=domain_scores.get)

        # 找到该领域下所有Agent / Find agents in this domain
        domain_caps = self._domain_groups[best_domain]
        agents = []
        for name, manifest in self._registry.items():
            if any(c in domain_caps for c in manifest.capabilities):
                cap_score = max(
                    score_map.get(c, 0.0) for c in manifest.capabilities
                )
                agents.append((manifest, cap_score))

        return sorted(agents, key=lambda x: x[1], reverse=True)

    def _route_agents(self, score_map: dict[AgentCapability, float],
                       strategy: FallbackStrategy,
                       threshold: float) -> list[tuple[AgentManifest, float]]:
        """Agent级路由 / Agent-level routing."""
        result: dict[str, float] = {}
        for cap, cap_score in sorted(
            score_map.items(), key=lambda x: x[1], reverse=True
        ):
            for agent_name, manifest in self._registry.items():
                if cap in manifest.capabilities:
                    if agent_name not in result or cap_score > result[agent_name]:
                        result[agent_name] = cap_score

        ranked = sorted(result.items(), key=lambda x: x[1], reverse=True)

        # 应用回退策略 / Apply fallback strategy
        if strategy == FallbackStrategy.STRICT and threshold > 0:
            ranked = [(n, s) for n, s in ranked if s >= threshold]
        elif strategy == FallbackStrategy.RELAXED and threshold > 0:
            ranked = [(n, s) for n, s in ranked if s >= threshold * 0.5]
        elif strategy == FallbackStrategy.CASCADE and not ranked and threshold > 0:
            ranked = sorted(result.items(), key=lambda x: x[1], reverse=True)[:2]

        return [(self._registry[name], score) for name, score in ranked]

    def _find_agents_for_capability(
        self, cap: AgentCapability, score: float
    ) -> list[tuple[AgentManifest, float]]:
        """为指定能力查找匹配Agent / Find agents for capability."""
        agents = []
        for name, manifest in self._registry.items():
            if cap in manifest.capabilities:
                agents.append((manifest, score))
        return agents

    def _classify_confidence(self, score: float) -> ConfidenceLevel:
        """将分数映射为置信度等级 / Map score to confidence level."""
        if score >= 0.6:
            return ConfidenceLevel.HIGH
        elif score >= 0.3:
            return ConfidenceLevel.MEDIUM
        elif score > 0:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNKNOWN

    def _suggest_command(self, capability: Optional[AgentCapability],
                          query: str) -> str:
        """根据意图生成建议命令 / Generate suggested command."""
        if capability is None:
            return ""
        suggestions = {
            AgentCapability.FINANCE_PREDICTION: f"atlas ask '分析{query}的股票趋势'",
            AgentCapability.SCREENPLAY_WRITING: f"atlas ask '为{query}写一个剧本大纲'",
            AgentCapability.IMAGE_GENERATION: f"atlas ask '生成一张{query}的图片'",
            AgentCapability.VIDEO_PRODUCTION: f"atlas ask '制作关于{query}的视频'",
            AgentCapability.MARKET_MONITORING: f"atlas ask '监控{query}的市场行情'",
            AgentCapability.CROSS_DOMAIN_LEARNING: f"atlas ask '学习{query}相关的知识'",
            AgentCapability.ECOMMERCE_OPS: f"atlas ask '管理{query}的电商商品'",
            AgentCapability.SHORT_VIDEO_OPS: f"atlas ask '{query}的短视频策略'",
            AgentCapability.SWARM_SIMULATION: f"atlas ask '用群体智能分析{query}'",
            AgentCapability.SYSTEM_MONITORING: f"atlas ask '检查{query}的系统状态'",
            AgentCapability.FAULT_ANALYSIS: f"atlas ask '分析{query}的故障原因'",
            AgentCapability.TOKEN_MANAGEMENT: f"atlas ask '查看{query}的Token使用情况'",
            AgentCapability.CREATIVE_COORDINATION: f"atlas ask '协调{query}的创意项目'",
            AgentCapability.TASK_ORCHESTRATION: f"atlas ask '编排{query}的工作流'",
        }
        return suggestions.get(capability, "")

    # ------------------------------------------------------------------
    # Agent 查询方法
    # ------------------------------------------------------------------

    def get_agent(self, name: str) -> Optional[AgentManifest]:
        """按名称查找 Agent / Lookup agent by name."""
        return self._registry.get(name)

    def list_all(self) -> list[AgentManifest]:
        """列出所有注册 Agent / List all registered agents."""
        return list(self._registry.values())

    def list_by_capability(self, capability: AgentCapability) -> list[AgentManifest]:
        """按能力筛选 Agent / Filter agents by capability."""
        return [m for m in self._registry.values() if capability in m.capabilities]

    def list_capabilities(self) -> list[AgentCapability]:
        """列出所有已定义的能力 / List all defined capabilities."""
        return list(AgentCapability)

    @property
    def registry_size(self) -> int:
        """已注册 Agent 数量 / Number of registered agents."""
        return len(self._registry)


# ══════════════════════════════════════════════════════════════
# Architecture Module 集成组件
# ══════════════════════════════════════════════════════════════


class RouterComponent(ArchComponent):
    """可注册到 ComponentRegistry 的路由组件 /
    Router component that can be registered in the ComponentRegistry."""

    def __init__(self):
        super().__init__(
            name="router_engine",
            version="2.0.0",
            description="Hierarchical intent router with multi-intent decomposition",
            requires=["architecture_module"],
        )
        self._router: Optional[IntentRouter] = None
        self._registry_ref: Optional[ComponentRegistry] = None

    def set_dependencies(self, deps: dict[str, ArchComponent]) -> None:
        """依赖注入 / Dependency injection."""
        self._registry_ref = deps.get("architecture_module")

    def _do_init(self) -> bool:
        """初始化路由引擎 / Initialize router."""
        self._router = IntentRouter()
        return True

    def route(self, query: str, **kwargs) -> list:
        """委派给内部路由器 / Delegate to internal router."""
        if self._router is None:
            self._router = IntentRouter()
        return self._router.route(query, **kwargs)

    def analyze(self, query: str, **kwargs) -> IntentResult:
        """委派给内部路由器 / Delegate to internal router."""
        if self._router is None:
            self._router = IntentRouter()
        return self._router.analyze(query, **kwargs)

    def plan(self, query: str, **kwargs) -> RoutingPlan:
        """委派给内部路由器 / Delegate to internal router."""
        if self._router is None:
            self._router = IntentRouter()
        return self._router.plan(query, **kwargs)

    @property
    def router(self) -> IntentRouter:
        """获取内部路由器实例 / Get internal router instance."""
        if self._router is None:
            self._router = IntentRouter()
        return self._router


# ══════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════


def create_router() -> IntentRouter:
    """创建默认配置的路由器 / Create a router with default configuration."""
    return IntentRouter(registry=REGISTRY)


def route_query(query: str) -> list[tuple[AgentManifest, float]]:
    """快捷路由 / Quick route a query."""
    router = create_router()
    return router.route(query)


def create_router_component() -> RouterComponent:
    """创建可注册的架构组件 / Create a registerable architecture component."""
    return RouterComponent()
