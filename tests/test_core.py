#!/usr/bin/env python3
"""
Tests for Atlas Core — 核心编排器测试
========================================
Tests initialization, process pipeline, memory ops, and integrity checks.
测试初始化、处理流程、记忆操作和完整性检查。
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from atlas_core.core import Atlas, create_atlas
from atlas_core.router_engine import AgentCapability, IntentRouter


# ══════════════════════════════════════════════════════════════
# 初始化测试 / Initialization tests
# ══════════════════════════════════════════════════════════════

class TestInitialization:
    """Atlas 初始化 / Atlas initialization"""

    def test_default_initialization(self):
        """默认配置初始化 / Default initialization"""
        atlas = Atlas()
        assert atlas is not None
        assert atlas.router is not None
        assert isinstance(atlas.router, IntentRouter)
        assert atlas.router.registry_size == 14

    def test_all_agents_14_registered(self):
        """确认14个Agent全注册 / Confirm all 14 agents registered"""
        atlas = Atlas()
        agents = atlas.router.list_all()
        names = [a.name for a in agents]
        assert len(agents) == 14
        assert "finance-agent" in names
        assert "screenplay-agent" in names
        assert "image-gen-agent" in names
        assert "video-prod-agent" in names
        assert "market-monitor-agent" in names
        assert "cross-domain-learner" in names
        assert "ecommerce-agent" in names
        assert "short-video-agent" in names
        assert "swarm-sim-agent" in names
        assert "system-sentinel" in names
        assert "fault-analysis-agent" in names
        assert "token-budget-agent" in names
        assert "creative-coordinator" in names
        assert "task-orchestrator" in names

    def test_disabled_voice_and_memory(self):
        """禁用语音和记忆 / Disable voice and memory"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        assert atlas is not None
        assert atlas._voice_enabled is False
        assert atlas._memory_enabled is False
        assert atlas.router is not None

    def test_custom_data_dir(self):
        """自定义数据目录 / Custom data directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            atlas = Atlas(memory_enabled=False, data_dir=tmpdir)
            assert atlas._data_dir == tmpdir
            assert os.path.exists(tmpdir)

    def test_factory_function(self):
        """工厂函数 / Factory function"""
        atlas = create_atlas(voice_enabled=False, memory_enabled=False)
        assert atlas is not None
        assert isinstance(atlas, Atlas)


# ══════════════════════════════════════════════════════════════
# 核心处理流程测试 / Core process pipeline tests
# ══════════════════════════════════════════════════════════════

class TestProcess:
    """process() 方法 / process() method"""

    def setup_method(self):
        self.atlas = Atlas(voice_enabled=False, memory_enabled=False)

    def test_empty_input(self):
        """空输入 / Empty input"""
        result = self.atlas.process("")
        assert result["intent"] == "error"
        assert result["confidence"] == 0.0
        assert "Empty input" in result["response"]

    def test_whitespace_input(self):
        """空白输入 / Whitespace input"""
        result = self.atlas.process("   ")
        assert result["intent"] == "error"

    def test_finance_query_routing(self):
        """金融查询路由 / Finance query routing"""
        result = self.atlas.process("stock price of AAPL")
        assert result is not None
        assert "intent" in result
        assert result["intent"] == AgentCapability.FINANCE.value

    def test_screenplay_query_routing(self):
        """剧本查询路由 / Screenplay query routing"""
        result = self.atlas.process("write a screenplay for a horror movie")
        assert result["intent"] == AgentCapability.SCREENPLAY.value
        assert result["confidence"] > 0

    def test_image_gen_routing(self):
        """图像生成路由 / Image generation routing"""
        result = self.atlas.process("generate an image of a mountain")
        assert result["intent"] == AgentCapability.IMAGE_GEN.value
        assert result["confidence"] > 0

    def test_chinese_image_routing(self):
        """中文图像查询路由 / Chinese image query routing"""
        result = self.atlas.process("帮我画一张风景图")
        assert result["intent"] == AgentCapability.IMAGE_GEN.value
        assert result["confidence"] > 0, "Chinese IMAGE_GEN should match keywords: 画, 图, 风景"

    def test_video_routing(self):
        """视频查询路由 / Video query routing"""
        result = self.atlas.process("make a video about AI")
        assert result["intent"] == AgentCapability.VIDEO_PROD.value
        assert result["confidence"] > 0

    def test_market_monitor_routing(self):
        """市场监控路由 / Market monitor routing"""
        result = self.atlas.process("monitor the market trends today")
        assert result["intent"] == AgentCapability.MARKET_MONITOR.value
        assert result["confidence"] > 0

    def test_ecommerce_routing(self):
        """电商查询路由 / E-commerce routing"""
        result = self.atlas.process("check my product inventory")
        assert result["intent"] == AgentCapability.ECOMMERCE.value
        assert result["confidence"] > 0

    def test_system_sentinel_routing(self):
        """系统监控路由 / System sentinel routing"""
        result = self.atlas.process("check system health status")
        assert result["intent"] == AgentCapability.SYSTEM_SENTINEL.value
        assert result["confidence"] > 0

    def test_unknown_query(self):
        """未知查询 / Unknown query"""
        result = self.atlas.process("xyzzy flurbo garblex")
        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.0
        assert "not sure" in result["response"].lower() or "help" in result["response"].lower()

    def test_matched_agents_in_result(self):
        """结果包含匹配Agent / Result contains matched agents"""
        result = self.atlas.process("analyze AAPL stock")
        assert len(result["matched_agents"]) > 0
        assert isinstance(result["matched_agents"], list)
        assert "finance-agent" in [a[0] for a in result["matched_agents"]]

    def test_result_structure(self):
        """结果结构完整性 / Result structure completeness"""
        result = self.atlas.process("hello")
        required_keys = {"response", "intent", "confidence", "matched_agents",
                         "memories_recalled", "memory_context", "timestamp"}
        assert required_keys.issubset(result.keys())

    def test_conversation_history_grows(self):
        """对话历史增长 / Conversation history grows"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        assert len(atlas.conversation_history) == 0
        atlas.process("test query")
        assert len(atlas.conversation_history) == 2  # user + assistant
        atlas.process("another query")
        assert len(atlas.conversation_history) == 4

    def test_chinese_finance_routing(self):
        """中文金融查询 / Chinese finance query"""
        result = self.atlas.process("分析股票走势")
        assert result["intent"] == AgentCapability.FINANCE.value


# ══════════════════════════════════════════════════════════════
# 记忆操作测试 / Memory operations tests (with memory disabled)
# ══════════════════════════════════════════════════════════════

class TestMemoryOps:
    """记忆操作 / Memory operations"""

    def setup_method(self):
        self.atlas = Atlas(voice_enabled=False, memory_enabled=False)

    def test_remember_disabled(self):
        """记忆禁用时的 remember / Remember when memory disabled"""
        success = self.atlas.remember("test_key", "test content")
        assert success is False

    def test_recall_disabled(self):
        """记忆禁用时的 recall / Recall when memory disabled"""
        results = self.atlas.recall("test query")
        assert results == []

    def test_forget_disabled(self):
        """记忆禁用时的 forget / Forget when memory disabled"""
        success = self.atlas.forget("test_key")
        assert success is False


# ══════════════════════════════════════════════════════════════
# 语音操作测试 / Voice operations tests (disabled)
# ══════════════════════════════════════════════════════════════

class TestVoiceOps:
    """语音操作（禁用状态） / Voice operations (disabled)"""

    def setup_method(self):
        self.atlas = Atlas(voice_enabled=False, memory_enabled=False)

    def test_listen_disabled(self):
        """语音禁用时的 listen / Listen when voice disabled"""
        text = self.atlas.listen()
        assert text == ""

    def test_speak_disabled(self):
        """语音禁用时的 speak / Speak when voice disabled"""
        success = self.atlas.speak("hello")
        assert success is False


# ══════════════════════════════════════════════════════════════
# 系统信息测试 / System info tests
# ══════════════════════════════════════════════════════════════

class TestSystemInfo:
    """系统信息 / System information"""

    def setup_method(self):
        self.atlas = Atlas(voice_enabled=False, memory_enabled=False)

    def test_get_info_keys(self):
        """get_info 包含所有必要键 / get_info has all required keys"""
        info = self.atlas.get_info()
        assert "version" in info
        assert "voice_enabled" in info
        assert "memory_enabled" in info
        assert "data_dir" in info
        assert "agents_registered" in info
        assert "conversation_history" in info
        assert "queries_processed" in info
        assert "session_duration_seconds" in info

    def test_get_info_values(self):
        """get_info 值正确 / get_info values correct"""
        info = self.atlas.get_info()
        assert info["version"] == "0.1.0"
        assert info["voice_enabled"] is False
        assert info["memory_enabled"] is False
        assert info["agents_registered"] == 14
        assert info["queries_processed"] == 0

    def test_query_count_increments(self):
        """查询计数递增 / Query count increments"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        assert atlas._query_count == 0
        atlas.process("test")
        assert atlas._query_count == 1
        atlas.process("test2")
        atlas.process("test3")
        assert atlas._query_count == 3

    def test_check_returns_errors(self):
        """检查返回预期错误 / Check returns expected errors"""
        # Both voice and memory are disabled, so check() should report them
        # (unless they're disabled, which means they WON'T generate errors)
        errors = self.atlas.check()
        # With voice_enabled=False, voice should not be an error
        # With memory_enabled=False, memory should not be an error
        # Router should be fine
        voice_errors = [e for e in errors if "Voice" in e]
        memory_errors = [e for e in errors if "Memory" in e]
        if self.atlas._voice_enabled:
            assert len(voice_errors) > 0
        if self.atlas._memory_enabled:
            assert len(memory_errors) > 0
        router_errors = [e for e in errors if "Router" in e]
        assert len(router_errors) == 0, f"Router should be fine, got: {router_errors}"


# ══════════════════════════════════════════════════════════════
# 边界测试 / Edge case tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况 / Edge cases"""

    def test_special_characters_in_query(self):
        """特殊字符查询 / Special characters in query"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        result = atlas.process("@#$%^&*()")
        assert result is not None
        assert "response" in result

    def test_very_long_query(self):
        """超长查询 / Very long query"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        long_text = "stock " * 100
        result = atlas.process(long_text)
        assert result is not None
        assert result["intent"] == AgentCapability.FINANCE.value
        assert result["confidence"] > 0

    def test_mixed_chinese_english(self):
        """中英混合 / Mixed Chinese-English"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        result = atlas.process("分析AAPL stock price趋势")
        assert result["intent"] == AgentCapability.FINANCE.value

    def test_multiple_intents_first_wins(self):
        """多意图取最高 / Multiple intents, highest wins"""
        atlas = Atlas(voice_enabled=False, memory_enabled=False)
        result = atlas.process("stock price image generation")
        # Both finance and image_gen match, the highest confidence wins
        assert result["intent"] in (AgentCapability.FINANCE.value, AgentCapability.IMAGE_GEN.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
