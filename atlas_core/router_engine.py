#!/usr/bin/env python3
"""
Atlas Router Engine — 意图路由引擎
=====================================
Intent classification, agent dispatch, and result aggregation.
意图识别、Agent 分派与结果聚合。

Routes natural language queries to the correct specialized agent(s)
based on keyword patterns and confidence scoring.
通过关键词匹配和置信度评分，将自然语言查询路由到正确的专业 Agent。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# AgentCapability Enum — 14 种能力定义
# ══════════════════════════════════════════════════════════════

class AgentCapability(Enum):
    """Agent 能力枚举 / Agent capability enumeration (14 agents)"""
    FINANCE = "finance"                    # 金融预测 / Financial prediction
    SCREENPLAY = "screenplay"              # 剧本创作 / Screenplay writing
    IMAGE_GEN = "image_gen"                # 图像生成 / Image generation
    VIDEO_PROD = "video_prod"              # 视频制作 / Video production
    MARKET_MONITOR = "market_monitor"      # 市场监控 / Market monitoring
    CROSS_DOMAIN = "cross_domain"          # 跨领域学习 / Cross-domain learning
    ECOMMERCE = "ecommerce"                # 电商运营 / E-commerce operations
    SHORT_VIDEO = "short_video"            # 短视频运营 / Short video operations
    SWARM = "swarm"                        # 群体智能 / Swarm simulation
    SYSTEM_SENTINEL = "system_sentinel"    # 系统监控 / System monitoring
    FAULT_ANALYSIS = "fault_analysis"      # 故障分析 / Fault analysis
    TOKEN_BUDGET = "token_budget"          # Token 预算 / Token budget management
    CREATIVE_COORD = "creative_coord"      # 创意协调 / Creative coordination
    TASK_ORCHESTRATION = "task_orch"       # 任务编排 / Task orchestration


# ══════════════════════════════════════════════════════════════
# AgentManifest — Agent 注册信息
# ══════════════════════════════════════════════════════════════

@dataclass
class AgentManifest:
    """Agent 注册清单 / Agent registration manifest

    Attributes:
        name: Agent 名称 / agent name
        repo_url: GitHub 仓库地址 / repository URL
        capabilities: 能力列表 / list of capabilities
        description: 功能描述 / description
        pip_package: pip 包名 (可能未安装) / pip package name (may not be installed)
    """
    name: str
    repo_url: str
    capabilities: list[AgentCapability]
    description: str
    pip_package: str = ""


# ══════════════════════════════════════════════════════════════
# IntentResult — 路由结果
# ══════════════════════════════════════════════════════════════

@dataclass
class IntentResult:
    """意图路由结果 / Intent routing result"""
    query: str                                  # 原始查询 / original query
    primary_intent: Optional[AgentCapability]    # 主意图 / primary intent
    confidence: float                           # 置信度 0-1 / confidence score
    matched_agents: list[tuple[str, float]]     # [(agent_name, confidence), ...]
    suggested_command: str = ""                 # 建议命令 / suggested command string


# ══════════════════════════════════════════════════════════════
# REGISTRY — 14 个 Agent 的完整注册表
# ══════════════════════════════════════════════════════════════

REGISTRY: dict[str, AgentManifest] = {
    # 1. Finance Agent / 金融预测 Agent
    "finance-agent": AgentManifest(
        name="finance-agent",
        repo_url="https://github.com/596600892/finance-agent",
        capabilities=[AgentCapability.FINANCE],
        description="8维股票预测、因子分析、投资组合优化 / 8D stock prediction, factor analysis, portfolio optimization",
        pip_package="finance-agent",
    ),
    # 2. Screenplay Agent / 剧本创作 Agent
    "screenplay-agent": AgentManifest(
        name="screenplay-agent",
        repo_url="https://github.com/596600892/screenplay-agent",
        capabilities=[AgentCapability.SCREENPLAY],
        description="剧本写作、角色开发、情节结构分析 / Screenplay writing, character development, plot structure analysis",
        pip_package="screenplay-agent",
    ),
    # 3. Image Generation Agent / 图像生成 Agent
    "image-gen-agent": AgentManifest(
        name="image-gen-agent",
        repo_url="https://github.com/596600892/image-agent",
        capabilities=[AgentCapability.IMAGE_GEN],
        description="文本到图像生成、风格迁移、图像编辑 / Text-to-image generation, style transfer, image editing",
        pip_package="image-gen-agent",
    ),
    # 4. Video Production Agent / 视频制作 Agent
    "video-prod-agent": AgentManifest(
        name="video-prod-agent",
        repo_url="https://github.com/596600892/video-agent",
        capabilities=[AgentCapability.VIDEO_PROD],
        description="视频生成、编辑、字幕与特效 / Video generation, editing, subtitles and effects",
        pip_package="video-prod-agent",
    ),
    # 5. Market Monitor Agent / 市场监控 Agent
    "market-monitor-agent": AgentManifest(
        name="market-monitor-agent",
        repo_url="https://github.com/596600892/market-monitor",
        capabilities=[AgentCapability.MARKET_MONITOR],
        description="实时市场监控、趋势识别、风险预警 / Real-time market monitoring, trend identification, risk alerts",
        pip_package="market-monitor-agent",
    ),
    # 6. Cross-Domain Learner Agent / 跨领域学习 Agent
    "cross-domain-learner": AgentManifest(
        name="cross-domain-learner",
        repo_url="https://github.com/596600892/cross-domain-learner",
        capabilities=[AgentCapability.CROSS_DOMAIN],
        description="跨领域知识迁移、Idle-Learning 循环 / Cross-domain knowledge transfer, Idle-Learning loop",
        pip_package="cross-domain-learner",
    ),
    # 7. E-commerce Agent / 电商运营 Agent
    "ecommerce-agent": AgentManifest(
        name="ecommerce-agent",
        repo_url="https://github.com/596600892/ecommerce-agent",
        capabilities=[AgentCapability.ECOMMERCE],
        description="电商运营自动化、商品管理、订单分析 / E-commerce automation, product management, order analysis",
        pip_package="ecommerce-agent",
    ),
    # 8. Short Video Agent / 短视频运营 Agent
    "short-video-agent": AgentManifest(
        name="short-video-agent",
        repo_url="https://github.com/596600892/short-video-ops-agent",
        capabilities=[AgentCapability.SHORT_VIDEO],
        description="短视频策略、内容优化、数据分析 / Short video strategy, content optimization, data analysis",
        pip_package="short-video-agent",
    ),
    # 9. Swarm Simulation Agent / 群体智能 Agent
    "swarm-sim-agent": AgentManifest(
        name="swarm-sim-agent",
        repo_url="https://github.com/596600892/mirofish-simulator",
        capabilities=[AgentCapability.SWARM],
        description="群体智能模拟、预测聚合、共识机制 / Swarm simulation, prediction aggregation, consensus mechanisms",
        pip_package="swarm-sim-agent",
    ),
    # 10. System Sentinel Agent / 系统监控 Agent
    "system-sentinel": AgentManifest(
        name="system-sentinel",
        repo_url="https://github.com/596600892/system-sentinel",
        capabilities=[AgentCapability.SYSTEM_SENTINEL],
        description="服务健康监控、资源管理、异常检测 / Service health monitoring, resource management, anomaly detection",
        pip_package="system-sentinel",
    ),
    # 11. Fault Analysis Agent / 故障分析 Agent
    "fault-analysis-agent": AgentManifest(
        name="fault-analysis-agent",
        repo_url="https://github.com/596600892/deerflow-orchestrator",
        capabilities=[AgentCapability.FAULT_ANALYSIS],
        description="故障诊断、根因分析、恢复建议 / Fault diagnosis, root cause analysis, recovery suggestions",
        pip_package="fault-analysis-agent",
    ),
    # 12. Token Budget Agent / Token 预算 Agent
    "token-budget-agent": AgentManifest(
        name="token-budget-agent",
        repo_url="https://github.com/596600892/token-budget-agent",
        capabilities=[AgentCapability.TOKEN_BUDGET],
        description="Token 预算管理、成本优化、配额控制 / Token budget management, cost optimization, quota control",
        pip_package="token-budget-agent",
    ),
    # 13. Creative Coordinator Agent / 创意协调 Agent
    "creative-coordinator": AgentManifest(
        name="creative-coordinator",
        repo_url="https://github.com/596600892/creative-coordinator",
        capabilities=[AgentCapability.CREATIVE_COORD],
        description="创意项目编排、多模态创作管线 / Creative project orchestration, multi-modal creation pipeline",
        pip_package="creative-coordinator",
    ),
    # 14. Task Orchestration Agent / 任务编排 Agent
    "task-orchestrator": AgentManifest(
        name="task-orchestrator",
        repo_url="https://github.com/596600892/ceo-agent-orchestrator",
        capabilities=[AgentCapability.TASK_ORCHESTRATION],
        description="多 Agent 任务编排、依赖管理、工作流执行 / Multi-agent task orchestration, dependency management, workflow execution",
        pip_package="task-orchestrator",
    ),
}

# ══════════════════════════════════════════════════════════════
# 关键词模式定义 / Keyword patterns for intent classification
# ══════════════════════════════════════════════════════════════
# 每个能力对应一组触发关键词 / Each capability maps to trigger keywords
# 格式: {AgentCapability: { "keywords": [...], "weight": float }}

_INTENT_PATTERNS: dict[AgentCapability, dict] = {
    AgentCapability.FINANCE: {
        "keywords": [
            "stock", "stocks", "price", "prices", "earnings", "finance", "financial",
            "investment", "invest", "portfolio", "dividend", "market cap", "ticker",
            "predict", "prediction", "forecast", "quote", "trading", "analysis",
            "股票", "股价", "金融", "投资", "理财", "基金", "收益率", "财报",
        ],
        "weight": 1.0,
    },
    AgentCapability.SCREENPLAY: {
        "keywords": [
            "screenplay", "script", "scene", "dialogue", "plot", "character arc",
            "storyboard", "narrative", "剧本", "脚本", "台词", "情节", "角色", "叙事",
        ],
        "weight": 1.0,
    },
    AgentCapability.IMAGE_GEN: {
        "keywords": [
            "image", "picture", "photo", "generate", "draw", "illustration",
            "image generation", "text to image", "style transfer",
            "图像", "图片", "照片", "生成图片", "画图", "插图", "文生图", "风格迁移",
            "画", "图", "风景", "生成", "绘制", "构图", "画笔", "绘画",
        ],
        "weight": 1.0,
    },
    AgentCapability.VIDEO_PROD: {
        "keywords": [
            "video", "movie", "film", "animation", "edit", "produce",
            "video production", "video editing", "subtitle", "caption",
            "视频", "电影", "动画", "编辑视频", "制作视频", "字幕", "特效",
        ],
        "weight": 1.0,
    },
    AgentCapability.MARKET_MONITOR: {
        "keywords": [
            "market", "trend", "monitor", "surveillance", "alert", "risk",
            "market data", "real time", "quote",
            "市场", "行情", "监控", "趋势", "预警", "风险", "实时", "报价",
        ],
        "weight": 1.0,
    },
    AgentCapability.CROSS_DOMAIN: {
        "keywords": [
            "learn", "study", "knowledge", "cross domain", "transfer",
            "research", "insight", "discover",
            "学习", "研究", "知识", "跨领域", "迁移", "洞察", "发现",
        ],
        "weight": 0.8,
    },
    AgentCapability.ECOMMERCE: {
        "keywords": [
            "ecommerce", "e-commerce", "shop", "product", "inventory", "order",
            "listing", "fulfillment", "supplier",
            "电商", "商品", "订单", "库存", "店铺", "供应链", "上架", "发货",
        ],
        "weight": 1.0,
    },
    AgentCapability.SHORT_VIDEO: {
        "keywords": [
            "short video", "tiktok", "reels", "shorts", "viral", "content strategy",
            "engagement", "follower",
            "短视频", "抖音", "快手", "内容", "粉丝", "流量", "爆款", "运营",
        ],
        "weight": 1.0,
    },
    AgentCapability.SWARM: {
        "keywords": [
            "swarm", "consensus", "collective", "simulation", "agent swarm",
            "multi agent", "prediction market",
            "群体", "群智", "共识", "模拟", "多智能体", "预测市场",
        ],
        "weight": 0.9,
    },
    AgentCapability.SYSTEM_SENTINEL: {
        "keywords": [
            "system", "server", "health", "uptime", "monitoring", "resource",
            "cpu", "memory", "disk", "service",
            "系统", "服务器", "健康", "监控", "资源", "CPU", "内存", "磁盘", "服务",
        ],
        "weight": 1.0,
    },
    AgentCapability.FAULT_ANALYSIS: {
        "keywords": [
            "fault", "error", "bug", "crash", "failure", "diagnosis",
            "root cause", "debug", "exception",
            "故障", "错误", "崩溃", "异常", "诊断", "根因", "调试", "Bug",
        ],
        "weight": 1.0,
    },
    AgentCapability.TOKEN_BUDGET: {
        "keywords": [
            "token", "budget", "cost", "quota", "usage", "pricing",
            "token count", "limit", "rate limit",
            "Token", "预算", "成本", "配额", "用量", "计费", "限制",
        ],
        "weight": 0.9,
    },
    AgentCapability.CREATIVE_COORD: {
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
# IntentRouter — 意图路由核心类
# ══════════════════════════════════════════════════════════════

class IntentRouter:
    """意图路由器 / Intent Router

    Classifies natural language queries into Agent capabilities
    based on keyword pattern matching with confidence scoring.
    基于关键词模式匹配和置信度评分，将自然语言查询分类到 Agent 能力。
    """

    def __init__(self, registry: Optional[dict[str, AgentManifest]] = None):
        """初始化路由器 / Initialize the router

        Args:
            registry: Agent 注册表，默认使用全局 REGISTRY / agent registry, defaults to global REGISTRY
        """
        self._registry = registry or REGISTRY
        self._patterns = _INTENT_PATTERNS

    # ------------------------------------------------------------------
    # 核心路由方法 / Core routing
    # ------------------------------------------------------------------

    def route(self, query: str) -> list[tuple[AgentManifest, float]]:
        """对查询进行意图分类 / Classify the intent of a query

        Args:
            query: 用户输入的自然语言 / user's natural language input

        Returns:
            按置信度降序排列的 (AgentManifest, 置信度) 列表 /
            list of (AgentManifest, confidence) sorted by confidence descending
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        score_map: dict[AgentCapability, float] = {}

        # 对每种能力进行关键词评分 / Score each capability by keyword matches
        for capability, pattern in self._patterns.items():
            score = self._score_intent(query_lower, capability, pattern)
            if score > 0:
                score_map[capability] = score

        # 如果没有匹配，返回空 / No matches
        if not score_map:
            return []

        # 按分数降序排列能力 / Sort capabilities by score descending
        sorted_caps = sorted(score_map.items(), key=lambda x: x[1], reverse=True)

        # 找出匹配这些能力的 Agents / Find agents matching these capabilities
        result_agents: dict[str, float] = {}
        for cap, cap_score in sorted_caps:
            for agent_name, manifest in self._registry.items():
                if cap in manifest.capabilities:
                    # 同一 Agent 取最高分 / Take highest score for same agent
                    if agent_name not in result_agents or cap_score > result_agents[agent_name]:
                        result_agents[agent_name] = cap_score

        # 构建返回结果 / Build return list
        ranked: list[tuple[AgentManifest, float]] = [
            (self._registry[name], score)
            for name, score in sorted(result_agents.items(), key=lambda x: x[1], reverse=True)
        ]

        return ranked

    def analyze(self, query: str) -> IntentResult:
        """全面分析查询意图 / Full intent analysis of a query

        Returns:
            包含完整路由信息的 IntentResult / IntentResult with full routing info
        """
        matched = self.route(query)

        if not matched:
            return IntentResult(
                query=query,
                primary_intent=None,
                confidence=0.0,
                matched_agents=[],
                suggested_command="",
            )

        primary_manifest, primary_conf = matched[0]
        primary_cap = primary_manifest.capabilities[0] if primary_manifest.capabilities else None

        matched_info = [(m.name, c) for m, c in matched]

        # 生成建议命令 / Generate suggested command
        suggested = self._suggest_command(primary_cap, query)

        return IntentResult(
            query=query,
            primary_intent=primary_cap,
            confidence=primary_conf,
            matched_agents=matched_info,
            suggested_command=suggested,
        )

    # ------------------------------------------------------------------
    # 内部方法 / Internal methods
    # ------------------------------------------------------------------

    def _score_intent(self, query_lower: str, capability: AgentCapability, pattern: dict) -> float:
        """计算查询与能力的匹配分数 / Calculate match score between query and capability

        Uses keyword-to-query ratio: matched_keywords / total_query_words.
        使用关键词匹配率：匹配关键词数 / 查询总词数。
        """
        keywords = pattern["keywords"]
        weight = pattern.get("weight", 1.0)
        query_words = query_lower.split()
        if not query_words:
            return 0.0

        # 统计匹配的唯一关键词数 / Count unique matching keywords
        matched_kw = 0
        for keyword in keywords:
            kw_lower = keyword.lower()
            if kw_lower in query_lower:
                matched_kw += 1

        if matched_kw == 0:
            return 0.0

        # 匹配关键词数 / 查询词数 = 匹配密度，上限1.0
        # matched_keywords / total_query_words = match density, capped at 1.0
        raw = matched_kw / len(query_words)
        normalized = min(raw, 1.0)
        return round(normalized * weight, 4)

    def _suggest_command(self, capability: Optional[AgentCapability], query: str) -> str:
        """根据意图生成建议命令 / Generate suggested command from intent"""
        if capability is None:
            return ""
        suggestions = {
            AgentCapability.FINANCE: f"atlas ask '分析{query}的股票趋势'",
            AgentCapability.SCREENPLAY: f"atlas ask '为{query}写一个剧本大纲'",
            AgentCapability.IMAGE_GEN: f"atlas ask '生成一张{query}的图片'",
            AgentCapability.VIDEO_PROD: f"atlas ask '制作关于{query}的视频'",
            AgentCapability.MARKET_MONITOR: f"atlas ask '监控{query}的市场行情'",
            AgentCapability.CROSS_DOMAIN: f"atlas ask '学习{query}相关的知识'",
            AgentCapability.ECOMMERCE: f"atlas ask '管理{query}的电商商品'",
            AgentCapability.SHORT_VIDEO: f"atlas ask '{query}的短视频策略'",
            AgentCapability.SWARM: f"atlas ask '用群体智能分析{query}'",
            AgentCapability.SYSTEM_SENTINEL: f"atlas ask '检查{query}的系统状态'",
            AgentCapability.FAULT_ANALYSIS: f"atlas ask '分析{query}的故障原因'",
            AgentCapability.TOKEN_BUDGET: f"atlas ask '查看{query}的Token使用情况'",
            AgentCapability.CREATIVE_COORD: f"atlas ask '协调{query}的创意项目'",
            AgentCapability.TASK_ORCHESTRATION: f"atlas ask '编排{query}的工作流'",
        }
        return suggestions.get(capability, "")

    # ------------------------------------------------------------------
    # 查询方法 / Query methods
    # ------------------------------------------------------------------

    def get_agent(self, name: str) -> Optional[AgentManifest]:
        """按名称查找 Agent / Lookup agent by name

        Args:
            name: Agent 名称 / agent name

        Returns:
            AgentManifest 或 None / AgentManifest or None if not found
        """
        return self._registry.get(name)

    def list_all(self) -> list[AgentManifest]:
        """列出所有注册的 Agent / List all registered agents

        Returns:
            所有 Agent 清单列表 / list of all agent manifests
        """
        return list(self._registry.values())

    def list_by_capability(self, capability: AgentCapability) -> list[AgentManifest]:
        """按能力筛选 Agent / Filter agents by capability

        Args:
            capability: 目标能力 / target capability

        Returns:
            具有该能力的 Agent 列表 / agents with the given capability
        """
        return [
            manifest for manifest in self._registry.values()
            if capability in manifest.capabilities
        ]

    def list_capabilities(self) -> list[AgentCapability]:
        """列出所有已定义的能力 / List all defined capabilities"""
        return list(AgentCapability)

    @property
    def registry_size(self) -> int:
        """已注册 Agent 数量 / Number of registered agents"""
        return len(self._registry)


# ══════════════════════════════════════════════════════════════
# 便捷函数 / Convenience functions
# ══════════════════════════════════════════════════════════════

def create_router() -> IntentRouter:
    """创建默认配置的路由器 / Create a router with default configuration"""
    return IntentRouter(registry=REGISTRY)


def route_query(query: str) -> list[tuple[AgentManifest, float]]:
    """快捷路由 / Quick route a query (one-shot)"""
    router = create_router()
    return router.route(query)
