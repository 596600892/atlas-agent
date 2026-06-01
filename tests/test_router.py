"""
Tests for Router Engine v2 — 路由引擎 v2 测试
==============================================
Phase 5: Hierarchical routing, multi-intent, LLM, fallback, aggregation.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from unittest.mock import patch, MagicMock

import pytest

from atlas_core.router_engine import (
    AgentCapability,
    AgentManifest,
    IntentResult,
    IntentRouter,
    REGISTRY,
    create_router,
    route_query,
    LLMEnhancer,
    RouterComponent,
    RoutingPlan,
    RouteLevel,
    ConfidenceLevel,
    FallbackStrategy,
    AggregationStrategy,
)


# ══════════════════════════════════════════════════════════════
# 注册表测试 / Registry tests
# ══════════════════════════════════════════════════════════════


class TestRegistry:
    """Agent 注册表测试 / Agent registry tests."""

    def test_all_14_agents_registered(self):
        assert len(REGISTRY) == 14

    def test_required_agents_present(self):
        required = [
            "finance-agent", "screenplay-agent", "image-gen-agent",
            "video-prod-agent", "market-monitor-agent", "cross-domain-learner",
            "ecommerce-agent", "short-video-agent", "swarm-sim-agent",
            "system-sentinel", "fault-analysis-agent", "token-budget-agent",
            "creative-coordinator", "task-orchestrator",
        ]
        for name in required:
            assert name in REGISTRY, f"Missing agent: {name}"

    def test_agent_manifest_structure(self):
        for name, manifest in REGISTRY.items():
            assert isinstance(manifest, AgentManifest)
            assert manifest.name
            assert manifest.repo_url
            assert manifest.capabilities
            assert manifest.description
            assert manifest.pip_package
            assert len(manifest.capabilities) >= 1

    def test_capability_enum_imported_from_architecture(self):
        """验证能力枚举来自 architecture.py / Verify capabilities from architecture."""
        expected = [
            "finance_prediction", "screenplay_writing", "image_generation",
            "video_production", "market_monitoring", "cross_domain_learning",
            "ecommerce_ops", "short_video_ops", "swarm_simulation",
            "system_monitoring", "fault_analysis", "token_management",
            "creative_coordination", "task_orchestration",
            "memory_management", "voice_interaction", "architecture", "plugin",
        ]
        actual = [c.value for c in AgentCapability]
        for v in expected:
            assert v in actual, f"Missing capability: {v}"

    def test_agent_capability_consistency(self):
        all_values = set(c.value for c in AgentCapability)
        for manifest in REGISTRY.values():
            for cap in manifest.capabilities:
                assert cap.value in all_values, (
                    f"{manifest.name} has unknown: {cap.value}"
                )


# ══════════════════════════════════════════════════════════════
# 意图分类测试 / Intent classification
# ══════════════════════════════════════════════════════════════


class TestIntentClassification:
    """意图分类测试 / Intent classification tests."""

    def setup_method(self):
        self.router = create_router()

    # --- Finance ---

    def test_finance_stock_query(self):
        results = self.router.route("what is the stock price of AAPL")
        assert len(results) > 0
        assert AgentCapability.FINANCE_PREDICTION in results[0][0].capabilities

    def test_finance_investment_query(self):
        results = self.router.route("我想投资股票")
        assert len(results) > 0
        assert AgentCapability.FINANCE_PREDICTION in results[0][0].capabilities

    def test_finance_earnings_query(self):
        results = self.router.route("show me earnings reports for tech stocks")
        assert len(results) > 0
        assert AgentCapability.FINANCE_PREDICTION in results[0][0].capabilities

    # --- Screenplay ---

    def test_screenplay_script_query(self):
        results = self.router.route("write a screenplay about time travel")
        assert len(results) > 0
        assert AgentCapability.SCREENPLAY_WRITING in results[0][0].capabilities

    def test_screenplay_dialogue_query(self):
        results = self.router.route("帮我写一段电影台词")
        assert len(results) > 0
        assert AgentCapability.SCREENPLAY_WRITING in results[0][0].capabilities

    # --- Image ---

    def test_image_gen_query(self):
        results = self.router.route("generate an image of a cat")
        assert len(results) > 0
        assert AgentCapability.IMAGE_GENERATION in results[0][0].capabilities

    def test_image_gen_chinese(self):
        results = self.router.route("帮我画一张风景图")
        assert len(results) > 0
        assert AgentCapability.IMAGE_GENERATION in results[0][0].capabilities

    # --- Video ---

    def test_video_production_query(self):
        results = self.router.route("edit this video with subtitles")
        assert len(results) > 0
        assert AgentCapability.VIDEO_PRODUCTION in results[0][0].capabilities

    # --- Market ---

    def test_market_monitor_query(self):
        results = self.router.route("monitor the stock market trends")
        assert len(results) > 0
        assert AgentCapability.MARKET_MONITORING in results[0][0].capabilities

    def test_market_alert_query(self):
        results = self.router.route("set up a risk alert for crypto")
        assert len(results) > 0
        assert AgentCapability.MARKET_MONITORING in results[0][0].capabilities

    # --- Cross-domain ---

    def test_cross_domain_query(self):
        results = self.router.route("learn about quantum computing")
        assert len(results) > 0
        assert AgentCapability.CROSS_DOMAIN_LEARNING in results[0][0].capabilities

    # --- E-commerce ---

    def test_ecommerce_query(self):
        results = self.router.route("manage my e-commerce inventory")
        assert len(results) > 0
        assert AgentCapability.ECOMMERCE_OPS in results[0][0].capabilities

    # --- Short Video ---

    def test_short_video_query(self):
        results = self.router.route("optimize my tiktok content strategy")
        assert len(results) > 0
        assert AgentCapability.SHORT_VIDEO_OPS in results[0][0].capabilities

    def test_short_video_chinese(self):
        results = self.router.route("抖音运营策略")
        assert len(results) > 0
        assert AgentCapability.SHORT_VIDEO_OPS in results[0][0].capabilities

    # --- Swarm ---

    def test_swarm_query(self):
        results = self.router.route("run a swarm simulation")
        assert len(results) > 0
        assert AgentCapability.SWARM_SIMULATION in results[0][0].capabilities

    # --- System ---

    def test_system_query(self):
        results = self.router.route("check system health and cpu usage")
        assert len(results) > 0
        assert AgentCapability.SYSTEM_MONITORING in results[0][0].capabilities

    # --- Fault ---

    def test_fault_query(self):
        results = self.router.route("analyze this crash error")
        assert len(results) > 0
        assert AgentCapability.FAULT_ANALYSIS in results[0][0].capabilities

    # --- Token ---

    def test_token_query(self):
        results = self.router.route("check my token usage and cost")
        assert len(results) > 0
        assert AgentCapability.TOKEN_MANAGEMENT in results[0][0].capabilities

    # --- Creative ---

    def test_creative_query(self):
        results = self.router.route("coordinate the creative project pipeline")
        assert len(results) > 0
        assert AgentCapability.CREATIVE_COORDINATION in results[0][0].capabilities

    # --- Task ---

    def test_task_query(self):
        results = self.router.route("orchestrate a multi-step workflow")
        assert len(results) > 0
        assert AgentCapability.TASK_ORCHESTRATION in results[0][0].capabilities


# ══════════════════════════════════════════════════════════════
# 置信度测试 / Confidence tests
# ══════════════════════════════════════════════════════════════


class TestConfidenceScoring:
    """置信度评分测试 / Confidence scoring tests."""

    def setup_method(self):
        self.router = create_router()

    def test_high_confidence_match(self):
        results = self.router.route("stock price prediction for AAPL")
        assert len(results) > 0
        assert results[0][1] > 0.5

    def test_medium_confidence_partial(self):
        results = self.router.route("我需要一些投资建议")
        assert len(results) > 0
        assert results[0][1] > 0

    def test_low_confidence_ambiguous(self):
        results = self.router.route("help")
        if results:
            assert results[0][1] < 0.5

    def test_confidence_ranking(self):
        results = self.router.route("stock market price analysis")
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]


# ══════════════════════════════════════════════════════════════
# 边界情况 / Edge cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """边界情况测试 / Edge case tests."""

    def setup_method(self):
        self.router = create_router()

    def test_empty_query(self):
        assert self.router.route("") == []

    def test_whitespace_query(self):
        assert self.router.route("   ") == []

    def test_gibberish_query(self):
        assert self.router.route("asdfqwer zxcvbnm") == []

    def test_special_characters(self):
        assert self.router.route("@#$%^&*()") == []

    def test_very_long_query(self):
        long_text = " ".join(["finance"] * 1000)
        results = self.router.route(long_text)
        assert len(results) > 0

    def test_mixed_language_query(self):
        results = self.router.route("帮我写一个 sci-fi screenplay about AI")
        assert len(results) > 0
        caps = {cap for m, _ in results for cap in m.capabilities}
        assert AgentCapability.SCREENPLAY_WRITING in caps

    def test_numeric_query(self):
        assert self.router.route("42") == []

    def test_single_character(self):
        assert self.router.route("a") == []


# ══════════════════════════════════════════════════════════════
# Agent 查找 / Agent lookup
# ══════════════════════════════════════════════════════════════


class TestAgentLookup:
    """Agent 查找测试 / Agent lookup tests."""

    def setup_method(self):
        self.router = create_router()

    def test_get_agent_found(self):
        agent = self.router.get_agent("finance-agent")
        assert agent is not None
        assert agent.name == "finance-agent"
        assert AgentCapability.FINANCE_PREDICTION in agent.capabilities

    def test_get_agent_not_found(self):
        assert self.router.get_agent("nonexistent") is None

    def test_get_agent_empty_name(self):
        assert self.router.get_agent("") is None

    def test_list_all_returns_14(self):
        assert len(self.router.list_all()) == 14

    def test_list_all_no_duplicates(self):
        names = [a.name for a in self.router.list_all()]
        assert len(names) == len(set(names))

    def test_list_by_capability_finance(self):
        agents = self.router.list_by_capability(AgentCapability.FINANCE_PREDICTION)
        assert len(agents) >= 1
        for agent in agents:
            assert AgentCapability.FINANCE_PREDICTION in agent.capabilities


# ══════════════════════════════════════════════════════════════
# IntentResult 测试 / IntentResult tests
# ══════════════════════════════════════════════════════════════


class TestIntentResult:
    """IntentResult 测试 / IntentResult tests."""

    def setup_method(self):
        self.router = create_router()

    def test_analyze_returns_intent_result(self):
        result = self.router.analyze("stock price of TSLA")
        assert isinstance(result, IntentResult)
        assert result.query == "stock price of TSLA"
        assert result.primary_intent is not None
        assert result.confidence > 0
        assert len(result.matched_agents) > 0

    def test_analyze_empty_query(self):
        result = self.router.analyze("")
        assert isinstance(result, IntentResult)
        assert result.primary_intent is None
        assert result.confidence == 0.0

    def test_analyze_unknown_query(self):
        result = self.router.analyze("xyzzy flurbo garblex")
        assert result.primary_intent is None
        assert result.confidence == 0.0

    def test_suggested_command(self):
        result = self.router.analyze("draw a picture of a mountain")
        assert result.suggested_command != ""
        assert "atlas ask" in result.suggested_command

    def test_no_suggestion_for_unknown(self):
        result = self.router.analyze("")
        assert result.suggested_command == ""


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 分层路由 / Hierarchical routing
# ══════════════════════════════════════════════════════════════


class TestHierarchicalRouting:
    """分层路由测试 / Hierarchical routing tests."""

    def setup_method(self):
        self.router = create_router()

    def test_agent_level_default(self):
        """默认是 AGENT 级别路由 / Default is AGENT level."""
        results = self.router.route("stock price AAPL")
        assert len(results) > 0
        assert results[0][0].name == "finance-agent"

    def test_domain_level_routing(self):
        """DOMAIN 级别返回领域下所有 Agent / Domain level returns domain agents."""
        results = self.router.route("stock market analysis",
                                     level=RouteLevel.DOMAIN)
        assert len(results) > 0
        # 金融领域应该包含 finance-agent
        names = [m.name for m, _ in results]
        assert "finance-agent" in names
        # 可能还包含 market-monitor-agent
        assert len(results) >= 1

    def test_domain_level_creative(self):
        """创意领域路由 / Creative domain routing."""
        results = self.router.route("draw a picture",
                                     level=RouteLevel.DOMAIN)
        assert len(results) > 0
        names = [m.name for m, _ in results]
        assert "image-gen-agent" in names

    def test_domain_level_tech(self):
        """技术领域路由 / Tech domain routing."""
        results = self.router.route("check system health",
                                     level=RouteLevel.DOMAIN)
        assert len(results) > 0
        names = [m.name for m, _ in results]
        assert "system-sentinel" in names

    def test_route_level_enum_values(self):
        """RouteLevel 枚举值正确 / RouteLevel enum has correct values."""
        assert RouteLevel.DOMAIN.value == "domain"
        assert RouteLevel.SUB_DOMAIN.value == "sub"
        assert RouteLevel.AGENT.value == "agent"


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 多意图分解 / Multi-intent decomposition
# ══════════════════════════════════════════════════════════════


class TestMultiIntentDecomposition:
    """多意图分解测试 / Multi-intent decomposition tests."""

    def setup_method(self):
        self.router = create_router()

    def test_decompose_single_intent(self):
        """单意图查询 / Single intent query."""
        results = self.router.decompose("stock price AAPL")
        assert len(results) >= 1

    def test_decompose_multi_intent(self):
        """复合意图: 画股票图 / Compound: draw stock chart."""
        results = self.router.decompose("draw a stock chart of AAPL")
        assert len(results) >= 1
        intents = [r.primary_intent for r in results if r.primary_intent]
        # 应该包含 IMAGE_GENERATION 和/或 FINANCE_PREDICTION
        assert any(
            AgentCapability.IMAGE_GENERATION in [r.primary_intent]
            for r in results
        ) or any(
            AgentCapability.FINANCE_PREDICTION in [r.primary_intent]
            for r in results
        )

    def test_decompose_empty_query(self):
        """空查询分解 / Empty query decomposition."""
        results = self.router.decompose("")
        assert results == []

    def test_decompose_gibberish(self):
        """无意义查询分解 / Gibberish decomposition."""
        results = self.router.decompose("asdf zxcv")
        assert results == []

    def test_decompose_returns_intent_result(self):
        """分解结果类型正确 / Decomposition returns correct type."""
        results = self.router.decompose("stock price AAPL")
        if results:
            assert isinstance(results[0], IntentResult)
            assert results[0].confidence > 0

    def test_decompose_confidence_level(self):
        """分解结果包含置信度等级 / Decomposition includes confidence level."""
        results = self.router.decompose("analyze stock for investment")
        if results:
            assert results[0].confidence_level is not None


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 路由计划 / Routing plan
# ══════════════════════════════════════════════════════════════


class TestRoutingPlan:
    """路由计划测试 / Routing plan tests."""

    def setup_method(self):
        self.router = create_router()

    def test_plan_single_intent(self):
        """单意图路由计划 / Single intent plan."""
        plan = self.router.plan("stock price AAPL")
        assert isinstance(plan, RoutingPlan)
        assert plan.query == "stock price AAPL"
        assert len(plan.decisions) >= 1
        assert plan.aggregate_confidence > 0

    def test_plan_strategy_first_match(self):
        """FIRST_MATCH 策略 / First match strategy."""
        plan = self.router.plan("stock price AAPL",
                                 strategy=AggregationStrategy.FIRST_MATCH)
        assert plan.aggregate_confidence >= 0

    def test_plan_strategy_merge(self):
        """MERGE 策略 / Merge strategy."""
        plan = self.router.plan("stock price AAPL",
                                 strategy=AggregationStrategy.MERGE)
        assert plan.aggregate_confidence >= 0

    def test_plan_strategy_weighted(self):
        """WEIGHTED 策略 / Weighted strategy."""
        plan = self.router.plan("stock price AAPL",
                                 strategy=AggregationStrategy.WEIGHTED)
        assert plan.aggregate_confidence >= 0

    def test_plan_empty_query(self):
        """空查询计划 / Empty query plan."""
        plan = self.router.plan("")
        assert plan.aggregate_confidence == 0.0

    def test_plan_aggregate_confidence_capped(self):
        """聚合置信度不超过 1.0 / Aggregate confidence capped at 1.0."""
        plan = self.router.plan("stock price AAPL")
        assert plan.aggregate_confidence <= 1.0


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 置信度等级 / Confidence levels
# ══════════════════════════════════════════════════════════════


class TestConfidenceLevel:
    """置信度等级测试 / Confidence level tests."""

    def test_high_confidence(self):
        router = create_router()
        result = router.analyze("stock price prediction for AAPL")
        assert result.confidence > 0.6
        assert result.confidence_level == ConfidenceLevel.HIGH

    def test_unknown_confidence(self):
        router = create_router()
        result = router.analyze("")
        assert result.confidence == 0.0
        assert result.confidence_level == ConfidenceLevel.UNKNOWN

    def test_confidence_level_enum(self):
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.UNKNOWN.value == "unknown"


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 回退策略 / Fallback strategies
# ══════════════════════════════════════════════════════════════


class TestFallbackStrategies:
    """回退策略测试 / Fallback strategy tests."""

    def setup_method(self):
        self.router = create_router()

    def test_strict_no_threshold(self):
        """无阈值的 STRICT 等同于默认 / STRICT without threshold equals default."""
        results = self.router.route("stock price",
                                     strategy=FallbackStrategy.STRICT)
        assert len(results) > 0

    def test_strict_with_threshold_passes(self):
        """STRICT + 低阈值仍匹配 / STRICT with low threshold still matches."""
        results = self.router.route("stock price AAPL",
                                     strategy=FallbackStrategy.STRICT,
                                     threshold=0.1)
        assert len(results) > 0

    def test_relaxed_lowers_threshold(self):
        """RELAXED 降低阈值 / RELAXED lowers threshold."""
        # 模糊查询在 STRICT+高阈值时可能空，RELAXED 应该能匹配
        strict_results = self.router.route("help",
                                            strategy=FallbackStrategy.STRICT,
                                            threshold=0.5)
        relaxed_results = self.router.route("help",
                                             strategy=FallbackStrategy.RELAXED,
                                             threshold=0.5)
        # RELAXED 应该比 STRICT 返回更多结果
        assert len(relaxed_results) >= len(strict_results)

    def test_fallback_strategy_enum(self):
        assert FallbackStrategy.STRICT.value == "strict"
        assert FallbackStrategy.RELAXED.value == "relaxed"
        assert FallbackStrategy.CASCADE.value == "cascade"


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: LLM增强 / LLM Enhancer
# ══════════════════════════════════════════════════════════════


class TestLLMEnhancer:
    """LLM 增强分类器测试 / LLM enhancer tests."""

    def test_not_available_by_default(self):
        """默认不可用 / Not available by default."""
        enhancer = LLMEnhancer()
        assert enhancer.available is False

    def test_available_with_url(self):
        """配置 URL 后可用 / Available with URL."""
        enhancer = LLMEnhancer(api_url="http://localhost:8642/v1/chat/completions")
        assert enhancer.available is True

    def test_classify_returns_empty_when_unavailable(self):
        """不可用时返回空 / Returns empty when unavailable."""
        enhancer = LLMEnhancer()
        result = enhancer.classify("test", [AgentCapability.FINANCE_PREDICTION])
        assert result == {}

    def test_classify_with_fallback_kw_only(self):
        """不可用时回退到关键词 / Fallback to keywords when unavailable."""
        enhancer = LLMEnhancer()
        kw_scores = {AgentCapability.FINANCE_PREDICTION: 0.5}
        result = enhancer.classify_with_fallback(
            "stock price",
            [AgentCapability.FINANCE_PREDICTION],
            kw_scores,
        )
        assert result == kw_scores

    def test_hybrid_with_high_kw(self):
        """关键词分数高时不用LLM / Skip LLM when keywords are confident."""
        enhancer = LLMEnhancer(api_url="http://localhost:8642/v1/chat/completions")
        kw_scores = {AgentCapability.FINANCE_PREDICTION: 0.8}
        result = enhancer.classify_with_fallback(
            "stock price AAPL",
            [AgentCapability.FINANCE_PREDICTION],
            kw_scores,
        )
        assert result[AgentCapability.FINANCE_PREDICTION] == 0.8


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: 聚合策略 / Aggregation strategies
# ══════════════════════════════════════════════════════════════


class TestAggregationStrategies:
    """聚合策略测试 / Aggregation strategy tests."""

    def test_enum_values(self):
        assert AggregationStrategy.FIRST_MATCH.value == "first"
        assert AggregationStrategy.WEIGHTED.value == "weighted"
        assert AggregationStrategy.MERGE.value == "merge"
        assert AggregationStrategy.PARALLEL.value == "parallel"


# ══════════════════════════════════════════════════════════════
# Phase 5 新功能测试: RouterComponent / Architecture integration
# ══════════════════════════════════════════════════════════════


class TestRouterComponent:
    """RouterComponent 测试 / Router component tests."""

    def test_create_component(self):
        """创建 RouterComponent / Create RouterComponent."""
        comp = RouterComponent()
        assert comp.name == "router_engine"
        assert comp.version == "2.0.0"
        assert "architecture_module" in comp.requires

    def test_router_created_on_demand(self):
        """懒初始化的路由 / Lazy initialized router."""
        comp = RouterComponent()
        router = comp.router
        assert router is not None
        assert router.registry_size > 0

    def test_component_route(self):
        """组件委派路由 / Component delegated routing."""
        comp = RouterComponent()
        results = comp.route("stock price")
        assert len(results) > 0

    def test_component_analyze(self):
        """组件委派分析 / Component delegated analysis."""
        comp = RouterComponent()
        result = comp.analyze("draw a picture")
        assert isinstance(result, IntentResult)
        assert result.primary_intent is not None

    def test_component_plan(self):
        """组件委派路由计划 / Component delegated routing plan."""
        comp = RouterComponent()
        plan = comp.plan("stock price")
        assert isinstance(plan, RoutingPlan)

    def test_component_init(self):
        """组件初始化 / Component initialization."""
        comp = RouterComponent()
        assert comp.init() is True
        assert comp.state.value == "running"


# ══════════════════════════════════════════════════════════════
# 便捷函数测试 / Convenience functions
# ══════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """便捷函数测试 / Convenience function tests."""

    def test_create_router(self):
        router = create_router()
        assert isinstance(router, IntentRouter)
        assert router.registry_size == 14

    def test_route_query(self):
        results = route_query("stock price AAPL")
        assert len(results) > 0
        assert results[0][0].name == "finance-agent"
