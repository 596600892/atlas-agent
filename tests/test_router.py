#!/usr/bin/env python3
"""
Tests for Router Engine — 路由引擎测试
=========================================
Tests intent classification, agent lookup, confidence scoring, and edge cases.
测试意图分类、Agent查找、置信度评分和边界情况。
"""

import sys
import os

# 确保测试能找到 atlas_core / Ensure tests can find atlas_core
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from atlas_core.router_engine import (
    AgentCapability,
    AgentManifest,
    IntentResult,
    IntentRouter,
    REGISTRY,
    create_router,
)


# ══════════════════════════════════════════════════════════════
# 基础测试 / Basic tests
# ══════════════════════════════════════════════════════════════

class TestRegistry:
    """测试 Agent 注册表 / Test agent registry"""

    def test_all_14_agents_registered(self):
        """验证所有14个Agent都已注册 / Verify all 14 agents are registered"""
        assert len(REGISTRY) == 14, f"Expected 14 agents, got {len(REGISTRY)}"

    def test_required_agents_present(self):
        """验证必需Agent存在 / Verify required agents exist"""
        required_names = [
            "finance-agent",
            "screenplay-agent",
            "image-gen-agent",
            "video-prod-agent",
            "market-monitor-agent",
            "cross-domain-learner",
            "ecommerce-agent",
            "short-video-agent",
            "swarm-sim-agent",
            "system-sentinel",
            "fault-analysis-agent",
            "token-budget-agent",
            "creative-coordinator",
            "task-orchestrator",
        ]
        for name in required_names:
            assert name in REGISTRY, f"Missing agent: {name}"

    def test_agent_manifest_structure(self):
        """验证AgentManifest结构完整 / Verify AgentManifest has all fields"""
        for name, manifest in REGISTRY.items():
            assert isinstance(manifest, AgentManifest), f"{name} is not AgentManifest"
            assert manifest.name, f"{name} has no name"
            assert manifest.repo_url, f"{name} has no repo_url"
            assert manifest.capabilities, f"{name} has no capabilities"
            assert manifest.description, f"{name} has no description"
            assert manifest.pip_package, f"{name} has no pip_package"
            # 每个Agent至少有一种能力 / Each agent has at least one capability
            assert len(manifest.capabilities) >= 1

    def test_capability_enum_values(self):
        """验证AgentCapability枚举值 / Verify enum values"""
        expected_values = [
            "finance",
            "screenplay",
            "image_gen",
            "video_prod",
            "market_monitor",
            "cross_domain",
            "ecommerce",
            "short_video",
            "swarm",
            "system_sentinel",
            "fault_analysis",
            "token_budget",
            "creative_coord",
            "task_orch",
        ]
        actual_values = [c.value for c in AgentCapability]
        for v in expected_values:
            assert v in actual_values, f"Missing capability value: {v}"
        assert len(actual_values) == 14

    def test_agent_capability_consistency(self):
        """验证Agent能力与枚举一致 / Verify agent capabilities match enum"""
        all_enum_values = set(c.value for c in AgentCapability)
        for manifest in REGISTRY.values():
            for cap in manifest.capabilities:
                assert cap.value in all_enum_values, (
                    f"{manifest.name} has unknown capability: {cap.value}"
                )


# ══════════════════════════════════════════════════════════════
# 路由测试 / Routing tests
# ══════════════════════════════════════════════════════════════

class TestIntentClassification:
    """测试意图分类 / Test intent classification"""

    def setup_method(self):
        self.router = create_router()

    # --- 金融 / Finance ---

    def test_finance_stock_query(self):
        """金融: 股票查询 / Finance: stock query"""
        results = self.router.route("what is the stock price of AAPL")
        assert len(results) > 0
        top_agent, confidence = results[0]
        assert AgentCapability.FINANCE in top_agent.capabilities
        assert confidence > 0.25, f"Expected >0.25, got {confidence}"

    def test_finance_investment_query(self):
        """金融: 投资查询 / Finance: investment query"""
        results = self.router.route("我想投资股票")
        assert len(results) > 0
        assert AgentCapability.FINANCE in results[0][0].capabilities

    def test_finance_earnings_query(self):
        """金融: 财报查询 / Finance: earnings query"""
        results = self.router.route("show me earnings reports for tech stocks")
        assert len(results) > 0
        assert AgentCapability.FINANCE in results[0][0].capabilities

    # --- 剧本 / Screenplay ---

    def test_screenplay_script_query(self):
        """剧本: 剧本查询 / Screenplay: script query"""
        results = self.router.route("write a screenplay about time travel")
        assert len(results) > 0
        assert AgentCapability.SCREENPLAY in results[0][0].capabilities

    def test_screenplay_dialogue_query(self):
        """剧本: 对话查询 / Screenplay: dialogue query"""
        results = self.router.route("帮我写一段电影台词")
        assert len(results) > 0
        assert AgentCapability.SCREENPLAY in results[0][0].capabilities

    # --- 图像 / Image ---

    def test_image_gen_query(self):
        """图像: 生成图片 / Image: generate image"""
        results = self.router.route("generate an image of a cat")
        assert len(results) > 0
        assert AgentCapability.IMAGE_GEN in results[0][0].capabilities

    def test_image_gen_chinese(self):
        """图像: 中文查询 / Image: Chinese query"""
        results = self.router.route("帮我画一张风景图")
        assert len(results) > 0
        assert AgentCapability.IMAGE_GEN in results[0][0].capabilities

    # --- 视频 / Video ---

    def test_video_production_query(self):
        """视频: 视频制作 / Video: video production"""
        results = self.router.route("edit this video with subtitles")
        assert len(results) > 0
        assert AgentCapability.VIDEO_PROD in results[0][0].capabilities

    # --- 市场 / Market ---

    def test_market_monitor_query(self):
        """市场: 市场监控 / Market: market monitor"""
        results = self.router.route("monitor the stock market trends")
        assert len(results) > 0
        assert AgentCapability.MARKET_MONITOR in results[0][0].capabilities

    def test_market_alert_query(self):
        """市场: 预警查询 / Market: alert query"""
        results = self.router.route("set up a risk alert for crypto")
        assert len(results) > 0
        assert AgentCapability.MARKET_MONITOR in results[0][0].capabilities

    # --- 跨领域 / Cross-domain ---

    def test_cross_domain_query(self):
        """跨领域: 学习查询 / Cross-domain: learning query"""
        results = self.router.route("learn about quantum computing")
        assert len(results) > 0
        assert AgentCapability.CROSS_DOMAIN in results[0][0].capabilities

    # --- 电商 / E-commerce ---

    def test_ecommerce_query(self):
        """电商: 商品查询 / E-commerce: product query"""
        results = self.router.route("manage my e-commerce inventory")
        assert len(results) > 0
        assert AgentCapability.ECOMMERCE in results[0][0].capabilities

    def test_ecommerce_order_query(self):
        """电商: 订单查询 / E-commerce: order query"""
        results = self.router.route("check my recent orders")
        assert len(results) > 0
        assert AgentCapability.ECOMMERCE in results[0][0].capabilities

    # --- 短视频 / Short Video ---

    def test_short_video_query(self):
        """短视频: 内容策略 / Short video: content strategy"""
        results = self.router.route("optimize my tiktok content strategy")
        assert len(results) > 0
        assert AgentCapability.SHORT_VIDEO in results[0][0].capabilities

    def test_short_video_chinese(self):
        """短视频: 中文查询 / Short video: Chinese query"""
        results = self.router.route("抖音运营策略")
        assert len(results) > 0
        assert AgentCapability.SHORT_VIDEO in results[0][0].capabilities

    # --- 群体智能 / Swarm ---

    def test_swarm_query(self):
        """群体智能: 模拟查询 / Swarm: simulation query"""
        results = self.router.route("run a swarm simulation")
        assert len(results) > 0
        assert AgentCapability.SWARM in results[0][0].capabilities

    # --- 系统监控 / System Sentinel ---

    def test_system_sentinel_query(self):
        """系统监控: 健康检查 / System: health check"""
        results = self.router.route("check system health and cpu usage")
        assert len(results) > 0
        assert AgentCapability.SYSTEM_SENTINEL in results[0][0].capabilities

    def test_system_server_query(self):
        """系统监控: 服务器查询 / System: server query"""
        results = self.router.route("monitor server memory")
        assert len(results) > 0
        assert AgentCapability.SYSTEM_SENTINEL in results[0][0].capabilities

    # --- 故障分析 / Fault Analysis ---

    def test_fault_analysis_query(self):
        """故障分析: 错误诊断 / Fault: error diagnosis"""
        results = self.router.route("analyze this crash error")
        assert len(results) > 0
        assert AgentCapability.FAULT_ANALYSIS in results[0][0].capabilities

    def test_fault_debug_query(self):
        """故障分析: 调试 / Fault: debug"""
        results = self.router.route("debug this exception in the code")
        assert len(results) > 0
        assert AgentCapability.FAULT_ANALYSIS in results[0][0].capabilities

    # --- Token预算 / Token Budget ---

    def test_token_budget_query(self):
        """Token预算: 用量查询 / Token: usage query"""
        results = self.router.route("check my token usage and cost")
        assert len(results) > 0
        assert AgentCapability.TOKEN_BUDGET in results[0][0].capabilities

    # --- 创意协调 / Creative Coord ---

    def test_creative_coord_query(self):
        """创意协调: 项目管理 / Creative: project management"""
        results = self.router.route("coordinate the creative project pipeline")
        assert len(results) > 0
        assert AgentCapability.CREATIVE_COORD in results[0][0].capabilities

    # --- 任务编排 / Task Orchestration ---

    def test_task_orchestration_query(self):
        """任务编排: 工作流 / Task: workflow"""
        results = self.router.route("orchestrate a multi-step workflow")
        assert len(results) > 0
        assert AgentCapability.TASK_ORCHESTRATION in results[0][0].capabilities

    def test_task_automation_query(self):
        """任务编排: 自动化 / Task: automation"""
        results = self.router.route("automate my deployment pipeline")
        assert len(results) > 0
        assert AgentCapability.TASK_ORCHESTRATION in results[0][0].capabilities


# ══════════════════════════════════════════════════════════════
# 置信度测试 / Confidence tests
# ══════════════════════════════════════════════════════════════

class TestConfidenceScoring:
    """测试置信度评分 / Test confidence scoring"""

    def setup_method(self):
        self.router = create_router()

    def test_high_confidence_exact_match(self):
        """高置信度: 精确匹配 / High confidence: exact match"""
        results = self.router.route("stock price prediction for AAPL")
        assert len(results) > 0
        assert results[0][1] > 0.5, f"Expected >0.5, got {results[0][1]}"

    def test_medium_confidence_partial_match(self):
        """中等置信度: 部分匹配 / Medium confidence: partial match"""
        results = self.router.route("我需要一些投资建议")
        assert len(results) > 0
        # 应该匹配到金融至少有一定分数 / Should match finance with some score
        assert results[0][1] > 0

    def test_low_confidence_ambiguous(self):
        """低置信度: 模糊查询 / Low confidence: ambiguous query"""
        results = self.router.route("help")
        # 大多数模糊查询至少会有一个低分匹配 / Most fuzzy queries match something at low score
        if results:
            assert results[0][1] < 0.5

    def test_confidence_ranking(self):
        """置信度排序: 最佳匹配排第一 / Confidence ranking: best match first"""
        results = self.router.route("stock market price analysis")
        if len(results) >= 2:
            # 金融应该排第一 / Finance should be first
            assert results[0][1] >= results[1][1]

    def test_multiple_keywords_increase_score(self):
        """多个关键词提高分数 / Multiple keywords increase score"""
        single = self.router.route("stock")
        multi = self.router.route("stock price earnings")
        if single and multi:
            assert multi[0][1] >= single[0][1]


# ══════════════════════════════════════════════════════════════
# 边界情况测试 / Edge case tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """测试边界情况 / Test edge cases"""

    def setup_method(self):
        self.router = create_router()

    def test_empty_query(self):
        """空查询 / Empty query"""
        results = self.router.route("")
        assert results == []

    def test_whitespace_query(self):
        """空白查询 / Whitespace-only query"""
        results = self.router.route("   ")
        assert results == []

    def test_gibberish_query(self):
        """无意义查询 / Gibberish query"""
        results = self.router.route("asdfqwer zxcvbnm")
        assert results == []

    def test_special_characters(self):
        """特殊字符 / Special characters"""
        results = self.router.route("@#$%^&*()")
        assert results == []

    def test_very_long_query(self):
        """超长查询 / Very long query"""
        long_text = " ".join(["finance"] * 1000)
        results = self.router.route(long_text)
        assert len(results) > 0
        assert AgentCapability.FINANCE in results[0][0].capabilities

    def test_mixed_language_query(self):
        """混合语言 / Mixed language"""
        results = self.router.route("帮我写一个 sci-fi screenplay about AI")
        assert len(results) > 0
        # 应该同时匹配剧本和创意 / Should match both screenplay and creative
        caps = {cap for m, _ in results for cap in m.capabilities}
        assert AgentCapability.SCREENPLAY in caps

    def test_numeric_query(self):
        """纯数字查询 / Numeric query"""
        results = self.router.route("42")
        assert results == []

    def test_single_character(self):
        """单字符 / Single character"""
        results = self.router.route("a")
        assert results == []


# ══════════════════════════════════════════════════════════════
# Agent查找测试 / Agent lookup tests
# ══════════════════════════════════════════════════════════════

class TestAgentLookup:
    """测试Agent查找方法 / Test agent lookup methods"""

    def setup_method(self):
        self.router = create_router()

    def test_get_agent_found(self):
        """查找存在的Agent / Lookup existing agent"""
        agent = self.router.get_agent("finance-agent")
        assert agent is not None
        assert agent.name == "finance-agent"
        assert AgentCapability.FINANCE in agent.capabilities

    def test_get_agent_not_found(self):
        """查找不存在的Agent / Lookup non-existent agent"""
        agent = self.router.get_agent("nonexistent-agent")
        assert agent is None

    def test_get_agent_empty_name(self):
        """空名称查找 / Empty name lookup"""
        agent = self.router.get_agent("")
        assert agent is None

    def test_list_all_returns_14(self):
        """list_all 返回14个 / list_all returns 14"""
        agents = self.router.list_all()
        assert len(agents) == 14

    def test_list_all_no_duplicates(self):
        """list_all 无重复 / list_all has no duplicates"""
        agents = self.router.list_all()
        names = [a.name for a in agents]
        assert len(names) == len(set(names))

    def test_list_by_capability_finance(self):
        """按金融能力筛选 / Filter by finance capability"""
        agents = self.router.list_by_capability(AgentCapability.FINANCE)
        assert len(agents) >= 1
        for agent in agents:
            assert AgentCapability.FINANCE in agent.capabilities

    def test_list_by_capability_unique_capabilities(self):
        """每种能力至少有一个Agent / Each capability has at least one agent"""
        for cap in AgentCapability:
            agents = self.router.list_by_capability(cap)
            assert len(agents) >= 1, f"No agents for capability: {cap}"


# ══════════════════════════════════════════════════════════════
# IntentResult 测试 / IntentResult tests
# ══════════════════════════════════════════════════════════════

class TestIntentResult:
    """测试 IntentResult / Test IntentResult"""

    def setup_method(self):
        self.router = create_router()

    def test_analyze_returns_intent_result(self):
        """analyze 返回 IntentResult / analyze returns IntentResult"""
        result = self.router.analyze("stock price of TSLA")
        assert isinstance(result, IntentResult)
        assert result.query == "stock price of TSLA"
        assert result.primary_intent is not None
        assert result.confidence > 0
        assert len(result.matched_agents) > 0

    def test_analyze_empty_query(self):
        """空查询分析 / Empty query analysis"""
        result = self.router.analyze("")
        assert isinstance(result, IntentResult)
        assert result.primary_intent is None
        assert result.confidence == 0.0
        assert result.matched_agents == []

    def test_analyze_unknown_query(self):
        """未知查询分析 / Unknown query analysis"""
        result = self.router.analyze("xyzzy flurbo garblex")
        assert isinstance(result, IntentResult)
        assert result.primary_intent is None
        assert result.confidence == 0.0

    def test_intent_result_suggested_command(self):
        """建议命令生成 / Suggested command generation"""
        result = self.router.analyze("draw a picture of a mountain")
        assert result.suggested_command != "", "Should have a suggested command"
        assert "atlas ask" in result.suggested_command

    def test_intent_result_no_suggestion_for_unknown(self):
        """未知查询无建议 / No suggestion for unknown query"""
        result = self.router.analyze("")
        assert result.suggested_command == ""
