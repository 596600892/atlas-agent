#!/usr/bin/env python3
"""
Atlas Core — 核心编排器
=========================
The brain that ties Voice Engine + Memory Engine + Router Engine together.
将语音引擎、记忆引擎和路由引擎整合为一体的大脑。

Atlas class provides the unified interface for all interactions:
- process(): route text input to the right agent
- remember() / recall(): persistent memory integration
- listen() / speak(): voice I/O (optional)
- run(): interactive REPL loop
"""

import json
import logging
import os
import shlex
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from atlas_core.router_engine import (
    AgentCapability,
    AgentManifest,
    IntentResult,
    IntentRouter,
    REGISTRY,
    create_router,
)

logger = logging.getLogger("atlas.core")

# ---------------------------------------------------------------------------
# 语音引擎的惰性导入 / Lazy import for voice engine (optional dependency)
# ---------------------------------------------------------------------------


def _import_voice():
    """尝试导入语音引擎 / Try to import the voice engine"""
    try:
        from atlas_core.voice_engine import (
            SpeechToText,
            TextToSpeech,
            Conversation,
            VoiceConfig,
        )
        return SpeechToText, TextToSpeech, Conversation, VoiceConfig
    except ImportError as e:
        logger.warning("Voice engine not available: %s", e)
        return None, None, None, None


def _import_memory():
    """尝试导入记忆引擎 / Try to import the memory engine"""
    try:
        from atlas_core.memory_engine import MemoryStore, ImportanceScorer, ContextInjector, create_memory_engine
        return MemoryStore, ImportanceScorer, ContextInjector, create_memory_engine
    except ImportError as e:
        logger.warning("Memory engine not available: %s", e)
        return None, None, None, None


# ---------------------------------------------------------------------------
# Atlas — 核心编排器
# ---------------------------------------------------------------------------

class Atlas:
    """Atlas 核心AI编排器 / Atlas Core AI Orchestrator

    整合所有模块的单一入口 / Single entry point integrating all modules:
      - 意图路由 (Router Engine) / Intent routing
      - 持久记忆 (Memory Engine) / Persistent memory
      - 语音交互 (Voice Engine, optional) / Voice interaction (optional)
      - 对话历史 (Conversation History) / Conversation tracking

    Usage / 使用方法:
        atlas = Atlas()
        result = atlas.process("分析AAPL股票")
        print(result["response"])
    """

    def __init__(
        self,
        voice_enabled: bool = True,
        memory_enabled: bool = True,
        data_dir: str = "~/.atlas",
    ):
        """初始化 Atlas / Initialize Atlas

        Args:
            voice_enabled: 是否启用语音 / enable voice I/O
            memory_enabled: 是否启用记忆 / enable persistent memory
            data_dir: 数据存储目录 / data storage directory
        """
        self._data_dir = os.path.expanduser(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

        # 路由引擎 / Router engine (always enabled)
        self.router = create_router()

        # 记忆引擎 / Memory engine (optional)
        self._memory_enabled = memory_enabled
        self._memory_store = None
        self._memory_scorer = None
        self._memory_injector = None
        self._init_memory()

        # 语音引擎 / Voice engine (optional)
        self._voice_enabled = voice_enabled
        self._stt = None
        self._tts = None
        self._conversation = None
        self._init_voice()

        # 对话历史 / Conversation history
        self.conversation_history: list[dict] = []
        self._max_history = 100  # 最大保留100条 / max 100 entries

        # 会话统计 / Session stats
        self._session_start = time.time()
        self._query_count = 0

        logger.info(
            "Atlas initialized | voice=%s | memory=%s | data_dir=%s",
            voice_enabled, memory_enabled, self._data_dir
        )

    # ------------------------------------------------------------------
    # 内部初始化 / Internal initialization
    # ------------------------------------------------------------------

    def _init_memory(self):
        """初始化记忆引擎 / Initialize memory engine"""
        if not self._memory_enabled:
            return
        MemoryStore, ImportanceScorer, ContextInjector, create_memory_engine = _import_memory()
        if create_memory_engine is None:
            self._memory_enabled = False
            logger.warning("Memory engine: disabled (import failed)")
            return

        db_path = os.path.join(self._data_dir, "atlas_memory.db")
        try:
            store, scorer, pruner, injector = create_memory_engine(db_path)
            self._memory_store = store
            self._memory_scorer = scorer
            self._memory_injector = injector
            logger.info("Memory engine: ready at %s", db_path)
        except Exception as e:
            self._memory_enabled = False
            logger.error("Memory engine: init failed — %s", e)

    def _init_voice(self):
        """初始化语音引擎 / Initialize voice engine"""
        if not self._voice_enabled:
            return
        SpeechToText, TextToSpeech, Conversation, VoiceConfig = _import_voice()
        if SpeechToText is None:
            self._voice_enabled = False
            logger.warning("Voice engine: disabled (import failed)")
            return

        try:
            config = VoiceConfig()
            self._stt = SpeechToText(config)
            self._tts = TextToSpeech(config)
            self._conversation = Conversation(config, stt=self._stt, tts=self._tts)
            logger.info("Voice engine: ready")
        except Exception as e:
            self._voice_enabled = False
            logger.error("Voice engine: init failed — %s", e)

    # ------------------------------------------------------------------
    # 核心处理方法 / Core process method
    # ------------------------------------------------------------------

    def process(self, text: str) -> dict:
        """处理用户输入 — 总入口 / Process user input — main entry

        完整流程 / Full pipeline:
          1. 记录对话历史 / Log to conversation history
          2. 路由意图 / Route the intent
          3. 检索相关记忆 / Recall relevant memories
          4. 构建响应 / Build response
          5. 保存到记忆 / Save to memory

        Args:
            text: 用户文本输入 / user text input

        Returns:
            dict with keys: response, intent, confidence, matched_agents,
            memories_recalled, timestamp
        """
        text = text.strip()
        if not text:
            return self._error_result("Empty input / 输入为空")

        self._query_count += 1
        timestamp = datetime.now(timezone.utc).isoformat()

        # Step 1: 记录对话历史 / Record conversation history
        self._add_to_history("user", text)

        # Step 2: 意图路由 / Route the intent
        intent_result = self.router.analyze(text)

        # Step 3: 检索相关记忆 / Recall relevant memories
        memories = []
        if self._memory_enabled and self._memory_store:
            try:
                memories = self._memory_store.recall(text, limit=5)
            except Exception as e:
                logger.warning("Memory recall failed: %s", e)

        # Step 4: 从记忆构建上下文 / Build context from memories
        memory_context = ""
        if memories:
            memory_lines = []
            for m in memories:
                content = m.get("content", "")
                key = m.get("key", "")
                if content:
                    memory_lines.append(f"[{key}] {content}")
            if memory_lines:
                memory_context = "Previously remembered / 之前记住的内容:\n" + "\n".join(memory_lines)

        # Step 5: 构建响应 / Build response
        response = self._build_response(text, intent_result, memory_context)

        # Step 6: 保存到记忆（重要对话） / Save important conversations to memory
        if self._memory_enabled and self._memory_store and intent_result.confidence > 0.3:
            try:
                self._memory_store.save(
                    key=f"conversation_{int(time.time())}",
                    content=f"Q: {text}\nA: {response}",
                    type="conversation",
                    tags=[intent_result.primary_intent.value if intent_result.primary_intent else "general"],
                    importance=min(intent_result.confidence, 0.9),
                )
            except Exception as e:
                logger.warning("Memory save failed: %s", e)

        # Step 7: 记录助手回复到历史 / Record assistant response
        self._add_to_history("assistant", response)

        return {
            "response": response,
            "intent": intent_result.primary_intent.value if intent_result.primary_intent else "unknown",
            "confidence": intent_result.confidence,
            "matched_agents": intent_result.matched_agents,
            "memories_recalled": len(memories),
            "memory_context": memory_context,
            "timestamp": timestamp,
        }

    # ------------------------------------------------------------------
    # 记忆操作方法 / Memory operations
    # ------------------------------------------------------------------

    def remember(self, key: str, content: str, type: str = "fact", tags: Optional[list[str]] = None) -> bool:
        """保存信息到长期记忆 / Save information to long-term memory

        Args:
            key: 记忆键名 / memory key
            content: 记忆内容 / memory content
            type: 记忆类型 (fact, preference, event, conversation) / memory type
            tags: 标签列表 / list of tags

        Returns:
            是否成功 / success flag
        """
        if not self._memory_enabled or not self._memory_store:
            logger.warning("Memory engine not available — cannot remember")
            return False

        try:
            self._memory_store.save(key=key, content=content, type=type, tags=tags or [])
            logger.info("Memory saved: key=%s type=%s", key, type)
            return True
        except Exception as e:
            logger.error("Failed to save memory: %s", e)
            return False

    def recall(self, query: str, limit: int = 5) -> list[dict]:
        """从长期记忆中检索 / Search long-term memory

        Args:
            query: 搜索关键词 / search query
            limit: 最大结果数 / max results

        Returns:
            记忆条目列表 / list of memory dicts
        """
        if not self._memory_enabled or not self._memory_store:
            return []
        try:
            return self._memory_store.recall(query, limit=limit)
        except Exception as e:
            logger.error("Memory recall failed: %s", e)
            return []

    def forget(self, key: str) -> bool:
        """删除特定记忆 / Delete a specific memory by key

        Args:
            key: 要删除的记忆键名 / memory key to delete

        Returns:
            是否成功 / success flag
        """
        if not self._memory_enabled or not self._memory_store:
            return False
        try:
            # MemoryStore doesn't have a direct delete by key, but it has a remove method
            # We'll try to find and remove
            results = self._memory_store.recall(key, limit=50)
            for m in results:
                if m.get("key") == key:
                    # 使用内部ID删除 / delete by internal ID
                    self._memory_store._conn.execute("DELETE FROM memories WHERE key=?", (key,))
                    self._memory_store._conn.commit()
                    return True
            return False
        except Exception as e:
            logger.error("Failed to forget: %s", e)
            return False

    # ------------------------------------------------------------------
    # 语音操作 / Voice operations
    # ------------------------------------------------------------------

    def listen(self) -> str:
        """语音输入 / Listen for voice input

        Returns:
            识别到的文本 / recognized text, or empty string on failure
        """
        if not self._voice_enabled or not self._stt:
            return ""
        try:
            text = self._stt.listen()
            if text:
                logger.info("Voice input: %s", text[:100])
            return text or ""
        except Exception as e:
            logger.warning("Voice input failed: %s", e)
            return ""

    def speak(self, text: str) -> bool:
        """语音输出 / Speak text aloud

        Args:
            text: 要朗读的文本 / text to speak

        Returns:
            是否成功 / success flag
        """
        if not self._voice_enabled or not self._tts:
            return False
        try:
            self._tts.speak(text)
            return True
        except Exception as e:
            logger.warning("Voice output failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # 交互运行循环 / Interactive run loop
    # ------------------------------------------------------------------

    def run(self, voice_mode: bool = False):
        """启动交互式对话循环 / Start interactive conversation loop

        Args:
            voice_mode: 是否使用语音模式 / use voice mode if True
        """
        print("╔══════════════════════════════════════════╗")
        print("║      Atlas — 通用人工智能体              ║")
        print("║      Universal AI Agent                  ║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  Voice: {'ON' if self._voice_enabled else 'OFF'}  |  "
              f"Memory: {'ON' if self._memory_enabled else 'OFF'}  ║")
        print("║  Type 'exit' or 'quit' to leave          ║")
        print("║  Type 'help' for available commands      ║")
        print("╚══════════════════════════════════════════╝")
        print()

        # 如果语音模式，先播报欢迎语 / If voice mode, speak welcome
        if voice_mode and self._voice_enabled:
            self.speak("Hello, I'm Atlas. How can I help you today?")

        while True:
            try:
                # 获取输入 / Get input
                if voice_mode and self._voice_enabled:
                    user_input = self.listen()
                    if not user_input:
                        continue
                    print(f"You (voice): {user_input}")
                else:
                    user_input = input("You: ").strip()

                if not user_input:
                    continue

                # 检查退出命令 / Check exit commands
                if user_input.lower() in ("exit", "quit", "bye", "再见", "退出"):
                    farewell = "Goodbye! Atlas signing off. / 再见！Atlas 离线。"
                    print(f"Atlas: {farewell}")
                    if voice_mode and self._voice_enabled:
                        self.speak(farewell)
                    break

                # 检查帮助命令 / Check help
                if user_input.lower() in ("help", "帮助", "h"):
                    self._print_help()
                    continue

                # 处理输入 / Process input
                result = self.process(user_input)

                # 输出响应 / Output response
                response = result["response"]
                print(f"Atlas: {response}")

                # 如果记忆有上下文，显示 / Show memory context if available
                if result.get("memory_context"):
                    print(f"  [Memory context: {result['memories_recalled']} items]")

                # 语音输出 / Voice output
                if voice_mode and self._voice_enabled:
                    self.speak(response[:500])  # 限制语音长度 / limit speech length

            except KeyboardInterrupt:
                print("\n\nGoodbye! / 再见！")
                break
            except EOFError:
                print("\nGoodbye! / 再见！")
                break
            except Exception as e:
                logger.error("Run loop error: %s", e)
                print(f"Atlas: Sorry, an error occurred: {e}")
                if voice_mode and self._voice_enabled:
                    self.speak("Sorry, an error occurred.")

    # ------------------------------------------------------------------
    # 内部方法 / Internal methods
    # ------------------------------------------------------------------

    def _build_response(self, text: str, intent: IntentResult, memory_context: str) -> str:
        """根据意图构建自然语言响应 / Build natural language response from intent"""
        if intent.confidence == 0.0:
            return (
                f"I'm not sure how to help with that. I can handle topics like "
                f"finance, images, video, e-commerce, system monitoring, and more. "
                f"Type 'help' to see what I can do.\n\n"
                f"我不知道如何帮您处理这个问题。我可以处理金融、图像、视频、电商、"
                f"系统监控等话题。输入 'help' 查看我的能力。"
            )

        primary = intent.primary_intent
        agent_name = intent.matched_agents[0][0] if intent.matched_agents else "unknown"

        # 按能力分类构建响应 / Build response by capability
        responses = {
            AgentCapability.FINANCE_PREDICTION: (
                f"I detected a finance-related query. The {agent_name} can help with "
                f"stock prediction, factor analysis, and portfolio optimization.\n\n"
                f"我识别到金融相关查询。{agent_name} 可以帮助进行股票预测、因子分析和投资组合优化。"
            ),
            AgentCapability.SCREENPLAY_WRITING: (
                f"I detected a screenplay-related query. The {agent_name} can help with "
                f"script writing, character development, and plot structure.\n\n"
                f"我识别到剧本相关查询。{agent_name} 可以帮助进行剧本写作、角色和情节开发。"
            ),
            AgentCapability.IMAGE_GENERATION: (
                f"I detected an image generation request. The {agent_name} can help with "
                f"text-to-image generation, style transfer, and image editing.\n\n"
                f"我识别到图像生成请求。{agent_name} 可以生成图像、风格迁移和图像编辑。"
            ),
            AgentCapability.VIDEO_PRODUCTION: (
                f"I detected a video production request. The {agent_name} can help with "
                f"video generation, editing, subtitles, and effects.\n\n"
                f"我识别到视频制作请求。{agent_name} 可以生成视频、编辑、添加字幕和特效。"
            ),
            AgentCapability.MARKET_MONITORING: (
                f"I detected a market monitoring request. The {agent_name} can help with "
                f"real-time market data, trend analysis, and risk alerts.\n\n"
                f"我识别到市场监控请求。{agent_name} 可以提供实时行情、趋势分析和风险预警。"
            ),
            AgentCapability.CROSS_DOMAIN_LEARNING: (
                f"I detected a learning-related query. The {agent_name} can help with "
                f"cross-domain knowledge transfer and research.\n\n"
                f"我识别到学习相关查询。{agent_name} 可以帮助跨领域知识迁移和研究。"
            ),
            AgentCapability.ECOMMERCE_OPS: (
                f"I detected an e-commerce query. The {agent_name} can help with "
                f"product management, order analysis, and inventory tracking.\n\n"
                f"我识别到电商相关查询。{agent_name} 可以帮助商品管理、订单分析和库存跟踪。"
            ),
            AgentCapability.SHORT_VIDEO_OPS: (
                f"I detected a short video query. The {agent_name} can help with "
                f"content strategy, engagement analysis, and trend optimization.\n\n"
                f"我识别到短视频相关查询。{agent_name} 可以提供内容策略、互动分析和趋势优化。"
            ),
            AgentCapability.SWARM_SIMULATION: (
                f"I detected a swarm intelligence query. The {agent_name} can help with "
                f"prediction aggregation, consensus mechanisms, and multi-agent simulation.\n\n"
                f"我识别到群体智能查询。{agent_name} 可以处理预测聚合、共识机制和多智能体模拟。"
            ),
            AgentCapability.SYSTEM_MONITORING: (
                f"I detected a system monitoring query. The {agent_name} can help with "
                f"service health checks, resource monitoring, and anomaly detection.\n\n"
                f"我识别到系统监控查询。{agent_name} 可以检查服务健康、监控资源和异常检测。"
            ),
            AgentCapability.FAULT_ANALYSIS: (
                f"I detected a fault analysis query. The {agent_name} can help with "
                f"error diagnosis, root cause analysis, and recovery planning.\n\n"
                f"我识别到故障分析查询。{agent_name} 可以诊断错误、分析根因和制定恢复计划。"
            ),
            AgentCapability.TOKEN_MANAGEMENT: (
                f"I detected a token budget query. The {agent_name} can help with "
                f"usage tracking, cost optimization, and quota management.\n\n"
                f"我识别到Token预算查询。{agent_name} 可以跟踪用量、优化成本和配额管理。"
            ),
            AgentCapability.CREATIVE_COORDINATION: (
                f"I detected a creative coordination query. The {agent_name} can help with "
                f"project pipeline management, multi-modal creation, and team collaboration.\n\n"
                f"我识别到创意协调查询。{agent_name} 可以管理项目管线、多模态创作和团队协作。"
            ),
            AgentCapability.TASK_ORCHESTRATION: (
                f"I detected a task orchestration query. The {agent_name} can help with "
                f"workflow automation, dependency management, and job scheduling.\n\n"
                f"我识别到任务编排查询。{agent_name} 可以自动化工作流、管理依赖和调度作业。"
            ),
        }

        base_response = responses.get(
            primary,
            f"I detected a query that maps to {agent_name} "
            f"(confidence: {intent.confidence * 100:.0f}%).\n\n"
            f"我识别到匹配 {agent_name} 的查询（置信度: {intent.confidence * 100:.0f}%）。"
        )

        # 添加记忆上下文信息 / Add memory context info
        if memory_context:
            base_response += f"\n\n[Memory / 记忆提示] {memory_context[:200]}"

        # 添加建议命令 / Add suggested command
        if intent.suggested_command:
            base_response += f"\n\nSuggested command / 建议命令: {intent.suggested_command}"

        return base_response

    def _add_to_history(self, role: str, content: str):
        """添加消息到对话历史 / Add a message to conversation history"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.conversation_history.append(entry)
        # 裁剪历史 / Trim history
        if len(self.conversation_history) > self._max_history:
            self.conversation_history = self.conversation_history[-self._max_history:]

    def _print_help(self):
        """打印帮助信息 / Print help information"""
        print("\n" + "=" * 60)
        print("Atlas Commands / Atlas 命令:")
        print("=" * 60)
        print("  exit, quit, bye     — Exit / 退出")
        print("  help                — Show this help / 显示帮助")
        print("  <any question>      — Ask me anything! / 问我任何问题！")
        print()
        print("Topics I can help with / 我可以帮助的话题:")
        print("-" * 40)
        for cap in AgentCapability:
            agents = self.router.list_by_capability(cap)
            names = ", ".join(a.name for a in agents)
            print(f"  {cap.value:20s} → {names}")
        print("=" * 60 + "\n")

    def _error_result(self, message: str) -> dict:
        """构造错误结果 / Build an error result dict"""
        return {
            "response": message,
            "intent": "error",
            "confidence": 0.0,
            "matched_agents": [],
            "memories_recalled": 0,
            "memory_context": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # 系统信息 / System info
    # ------------------------------------------------------------------

    def get_info(self) -> dict:
        """获取系统信息 / Get system information"""
        return {
            "version": "0.1.0",
            "voice_enabled": self._voice_enabled,
            "memory_enabled": self._memory_enabled,
            "data_dir": self._data_dir,
            "agents_registered": len(self.router.list_all()),
            "conversation_history": len(self.conversation_history),
            "queries_processed": self._query_count,
            "session_duration_seconds": int(time.time() - self._session_start),
        }

    def check(self) -> list[str]:
        """完整性检查 / Integrity check

        Returns:
            错误信息列表，空列表表示一切正常 / list of errors, empty if all good
        """
        errors = []

        # 检查路由引擎 / Check router
        if not self.router:
            errors.append("Router engine: NOT initialized")
        elif self.router.registry_size != 14:
            errors.append(f"Router engine: expected 14 agents, got {self.router.registry_size}")

        # 检查记忆引擎 / Check memory
        if self._memory_enabled and not self._memory_store:
            errors.append("Memory engine: configured but not initialized")
        elif not self._memory_enabled:
            errors.append("Memory engine: DISABLED (import failed)")

        # 检查语音引擎 / Check voice
        if self._voice_enabled and not self._stt:
            errors.append("Voice engine: configured but not initialized")
        elif not self._voice_enabled:
            errors.append("Voice engine: DISABLED (import or dependency missing)")

        return errors


# ══════════════════════════════════════════════════════════════
# 便捷工厂函数 / Convenience factory
# ══════════════════════════════════════════════════════════════

def create_atlas(
    voice_enabled: bool = True,
    memory_enabled: bool = True,
    data_dir: str = "~/.atlas",
) -> Atlas:
    """创建并返回配置好的 Atlas 实例 / Create and return a configured Atlas instance"""
    return Atlas(voice_enabled=voice_enabled, memory_enabled=memory_enabled, data_dir=data_dir)
