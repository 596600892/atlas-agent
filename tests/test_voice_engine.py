#!/usr/bin/env python3
"""
Atlas Voice Engine — Unit Tests / 单元测试
===============================================

测试 voice_engine.py 的所有核心组件。
Tests all core components of voice_engine.py.

Run with: pytest tests/test_voice_engine.py -v
"""

import queue
import time
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from atlas_core.voice_engine import (
    Conversation,
    ConversationState,
    SpeechToText,
    TextToSpeech,
    VoiceConfig,
    WakeWordDetector,
)


# ══════════════════════════════════════════════════════════════
# Fixtures / 测试夹具
# ══════════════════════════════════════════════════════════════


@pytest.fixture
def default_config():
    """默认测试配置 / Default test configuration."""
    return VoiceConfig(
        mic_index=None,
        energy_threshold=3000,
        pause_threshold=0.8,
        dynamic_energy=True,
        phrase_time_limit=10.0,
        language="en-US",
        timeout=2.0,
        retry_on_failure=1,
        wake_words=["hey atlas", "atlas"],
        wake_word_required=True,
        voice_rate=180,
        voice_volume=1.0,
        voice_id=None,
    )


@pytest.fixture
def wake_detector():
    """唤醒词检测器 / Wake word detector fixture."""
    return WakeWordDetector(wake_words=["hey atlas", "atlas", "hello atlas"])


# ══════════════════════════════════════════════════════════════
# WakeWordDetector Tests / 唤醒词检测器测试
# ══════════════════════════════════════════════════════════════


class TestWakeWordDetector:
    """唤醒词检测器单元测试 / Wake word detector unit tests."""

    def test_detect_exact_wake_word(self, wake_detector):
        """精确匹配唤醒词 / Exact wake word match."""
        result = wake_detector.contains_wake_word("hey atlas")
        assert result["detected"] is True
        assert result["wake_word"] == "hey atlas"
        assert result["confidence"] == 1.0

    def test_detect_wake_word_in_phrase(self, wake_detector):
        """唤醒词在短语中 / Wake word in longer phrase."""
        result = wake_detector.contains_wake_word("hey atlas what's the weather")
        assert result["detected"] is True
        assert result["wake_word"] == "hey atlas"
        assert result["confidence"] == 0.8

    def test_detect_case_insensitive(self, wake_detector):
        """大小写不敏感 / Case insensitive detection."""
        result = wake_detector.contains_wake_word("HEY ATLAS")
        assert result["detected"] is True
        assert result["wake_word"] == "hey atlas"

    def test_no_wake_word(self, wake_detector):
        """无唤醒词 / No wake word present."""
        result = wake_detector.contains_wake_word("what's the weather today")
        assert result["detected"] is False
        assert result["wake_word"] is None

    def test_empty_text(self, wake_detector):
        """空文本 / Empty text."""
        result = wake_detector.contains_wake_word("")
        assert result["detected"] is False

    def test_none_text(self, wake_detector):
        """None 文本 / None text."""
        result = wake_detector.contains_wake_word(None)
        assert result["detected"] is False

    def test_multiple_wake_words(self, wake_detector):
        """多个唤醒词之一 / One of multiple wake words."""
        result = wake_detector.contains_wake_word("hello atlas")
        assert result["detected"] is True
        assert result["wake_word"] == "hello atlas"

    def test_atlas_in_middle(self, wake_detector):
        """唤醒词在中间 / Wake word in middle of text."""
        result = wake_detector.contains_wake_word("please atlas help me")
        assert result["detected"] is True
        assert result["wake_word"] == "atlas"

    def test_strip_wake_word_prefix(self, wake_detector):
        """去掉唤醒词前缀 / Strip wake word prefix."""
        cleaned = wake_detector.strip_wake_word("hey atlas what's the weather")
        assert cleaned == "what's the weather"

    def test_strip_wake_word_no_prefix(self, wake_detector):
        """没有唤醒词前缀 / No wake word prefix."""
        cleaned = wake_detector.strip_wake_word("what's the weather")
        assert cleaned == "what's the weather"

    def test_strip_wake_word_exact(self, wake_detector):
        """只有唤醒词本身 / Only wake word."""
        cleaned = wake_detector.strip_wake_word("hey atlas")
        assert cleaned == ""

    def test_add_wake_word(self, wake_detector):
        """添加新唤醒词 / Add new wake word."""
        wake_detector.add_wake_word("computer")
        assert "computer" in wake_detector.phrases
        result = wake_detector.contains_wake_word("computer")
        assert result["detected"] is True

    def test_stats(self, wake_detector):
        """统计信息 / Statistics."""
        wake_detector.contains_wake_word("hey atlas")
        wake_detector.contains_wake_word("hello atlas")
        stats = wake_detector.stats
        assert stats["total_detections"] == 2
        assert stats["last_detected"] == "hello atlas"


# ══════════════════════════════════════════════════════════════
# VoiceConfig Tests / 配置测试
# ══════════════════════════════════════════════════════════════


class TestVoiceConfig:
    """配置单元测试 / Configuration unit tests."""

    def test_default_config(self):
        """默认配置值 / Default config values."""
        config = VoiceConfig()
        assert config.mic_index is None
        assert config.energy_threshold == 3000
        assert config.pause_threshold == 0.8
        assert config.language == "zh-CN"
        assert config.voice_rate == 180
        assert config.voice_volume == 1.0
        assert "atlas" in config.wake_words

    def test_custom_config(self):
        """自定义配置 / Custom config values."""
        config = VoiceConfig(
            mic_index=1,
            energy_threshold=4000,
            language="en-US",
            voice_rate=200,
        )
        assert config.mic_index == 1
        assert config.energy_threshold == 4000
        assert config.language == "en-US"
        assert config.voice_rate == 200


# ══════════════════════════════════════════════════════════════
# SpeechToText Tests (mocked) / 语音识别测试（模拟）
# ══════════════════════════════════════════════════════════════


class TestSpeechToText:
    """
    语音识别单元测试（无真实麦克风）/
    STT unit tests (no real microphone needed).

    Patches real speech_recognition classes directly.
    """

    def test_list_microphones(self):
        """列出麦克风 / List microphones."""
        with patch("speech_recognition.Microphone") as mock_mic_cls:
            mock_mic_cls.list_microphone_names.return_value = [
                "Built-in Microphone",
                "External USB Mic",
            ]
            # 模拟 Microphone 实例 / mock Microphone instances
            instance1 = MagicMock()
            instance2 = MagicMock()
            mock_mic_cls.side_effect = [instance1, instance2]

            stt = SpeechToText()
            mics = stt.list_microphones()
            assert len(mics) == 2
            assert mics[0]["name"] == "Built-in Microphone"
            assert mics[1]["name"] == "External USB Mic"

    def test_listen_success(self):
        """成功听取 / Successful listen."""
        with patch("speech_recognition.Recognizer") as mock_rec_cls, \
             patch("speech_recognition.Microphone") as mock_mic_cls:

            mock_recognizer = MagicMock()
            mock_recognizer.energy_threshold = 3000
            mock_recognizer.pause_threshold = 0.8
            mock_recognizer.dynamic_energy_threshold = True
            mock_rec_cls.return_value = mock_recognizer

            mock_mic = MagicMock()
            mock_mic.__enter__.return_value = mock_mic
            mock_mic.__exit__.return_value = None
            mock_mic_cls.return_value = mock_mic

            mock_audio = MagicMock()
            mock_audio.frame_data = b"\x00" * 16000 * 2
            mock_audio.sample_rate = 16000
            mock_audio.sample_width = 2
            mock_recognizer.listen.return_value = mock_audio

            mock_recognizer.recognize_google.return_value = "hello world"

            stt = SpeechToText()
            stt._initialized = False
            stt._recognizer = None
            stt._microphone = None

            result = stt.listen(timeout=2.0)
            assert result["success"] is True
            assert result["text"] == "hello world"
            assert result["error"] is None

    def test_listen_no_speech(self):
        """没有说话（超时）/ No speech detected (timeout)."""
        with patch("speech_recognition.Recognizer") as mock_rec_cls, \
             patch("speech_recognition.Microphone") as mock_mic_cls:

            mock_recognizer = MagicMock()
            mock_recognizer.energy_threshold = 3000
            mock_recognizer.pause_threshold = 0.8
            mock_recognizer.dynamic_energy_threshold = True
            mock_rec_cls.return_value = mock_recognizer

            mock_mic = MagicMock()
            mock_mic.__enter__.return_value = mock_mic
            mock_mic.__exit__.return_value = None
            mock_mic_cls.return_value = mock_mic

            # 模拟超时 / simulate timeout
            mock_recognizer.listen.side_effect = queue.Empty()

            stt = SpeechToText()
            stt._initialized = False
            stt._recognizer = None
            stt._microphone = None

            result = stt.listen(timeout=1.0)
            assert result["success"] is False
            assert result["error"] is not None
            assert "timeout" in result["error"].lower() or "silence" in result["error"].lower()

    def test_listen_unintelligible(self):
        """语音无法识别 / Speech unintelligible."""
        with patch("speech_recognition.Recognizer") as mock_rec_cls, \
             patch("speech_recognition.Microphone") as mock_mic_cls:

            mock_recognizer = MagicMock()
            mock_recognizer.energy_threshold = 3000
            mock_recognizer.pause_threshold = 0.8
            mock_recognizer.dynamic_energy_threshold = True
            mock_rec_cls.return_value = mock_recognizer

            mock_mic = MagicMock()
            mock_mic.__enter__.return_value = mock_mic
            mock_mic.__exit__.return_value = None
            mock_mic_cls.return_value = mock_mic

            mock_audio = MagicMock()
            mock_audio.frame_data = b"\x00" * 16000
            mock_audio.sample_rate = 16000
            mock_audio.sample_width = 2
            mock_recognizer.listen.return_value = mock_audio

            # 模拟 LookupError (built-in, caught by code) /
            # simulate LookupError (built-in, caught by code)
            mock_recognizer.recognize_google.side_effect = LookupError()

            stt = SpeechToText()
            stt._initialized = False
            stt._recognizer = None
            stt._microphone = None

            result = stt.listen(timeout=2.0)
            assert result["success"] is False
            assert result["error"] is not None

    def test_listen_os_error(self):
        """麦克风硬件错误 / Microphone hardware error."""
        with patch("speech_recognition.Recognizer") as mock_rec_cls, \
             patch("speech_recognition.Microphone") as mock_mic_cls:

            mock_recognizer = MagicMock()
            mock_recognizer.energy_threshold = 3000
            mock_recognizer.pause_threshold = 0.8
            mock_recognizer.dynamic_energy_threshold = True
            mock_rec_cls.return_value = mock_recognizer

            mock_mic = MagicMock()
            mock_mic.__enter__.return_value = mock_mic
            mock_mic.__exit__.return_value = None
            mock_mic_cls.return_value = mock_mic

            mock_recognizer.listen.side_effect = OSError("No input device")

            stt = SpeechToText()
            stt._initialized = False
            stt._recognizer = None
            stt._microphone = None

            result = stt.listen(timeout=2.0)
            assert result["success"] is False
            assert "Microphone" in result["error"] or "OSError" in result["error"] or "No input" in result["error"]

    def test_init_failure_no_dependency(self):
        """缺少依赖时的错误处理 / Error handling when dependency missing."""
        stt = SpeechToText()
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            stt._initialized = False
            stt._recognizer = None
            result = stt.listen()
            assert result["success"] is False
            assert result["error"] is not None

    def test_lazy_init_returns_false_on_import_error(self):
        """导入失败时延迟初始化返回 False /
        Lazy init returns False on import error."""
        stt = SpeechToText()
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = stt._lazy_init()
            assert result is False

    def test_listen_with_retry_hardware_error(self):
        """硬件错误时不重试 / Don't retry on hardware errors."""
        stt = SpeechToText()
        with patch.object(stt, "listen", return_value={
            "success": False,
            "error": "Microphone error: device not found",
            "text": None,
        }):
            result = stt.listen_with_retry(timeout=1.0)
            assert result["success"] is False
            assert "Microphone" in result["error"]


# ══════════════════════════════════════════════════════════════
# TextToSpeech Tests (mocked) / 语音合成测试（模拟）
# ══════════════════════════════════════════════════════════════


class TestTextToSpeech:
    """语音合成单元测试 / TTS unit tests."""

    def _make_mock_engine(self):
        """创建模拟 TTS 引擎 / Create a mock TTS engine."""
        mock_engine = MagicMock()
        return mock_engine

    def test_init_success(self):
        """初始化成功 / Successful initialization."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            assert tts._lazy_init() is True
            assert tts.is_available is True
            mock_init.assert_called_once()

    def test_init_sets_properties(self):
        """初始化时设置属性 / Properties set on init."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            config = VoiceConfig(voice_rate=200, voice_volume=0.8)
            tts = TextToSpeech(config=config)
            tts._lazy_init()

            mock_engine.setProperty.assert_any_call("rate", 200)
            mock_engine.setProperty.assert_any_call("volume", 0.8)

    def test_voices_property(self):
        """语音列表属性 / Voices list property."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            mock_voice = MagicMock()
            mock_voice.id = "com.apple.speech.synthesis.voice.samantha"
            mock_voice.name = "Samantha"
            mock_voice.languages = ["en-US"]
            mock_engine.getProperty.return_value = [mock_voice]

            tts = TextToSpeech()
            voices = tts.voices
            assert len(voices) == 1
            assert voices[0]["id"] == "com.apple.speech.synthesis.voice.samantha"

    def test_speak_blocking(self):
        """阻塞朗读 / Blocking speak."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.speak("Hello world", blocking=True)
            assert result["success"] is True
            assert result["text"] == "Hello world"
            mock_engine.say.assert_called_with("Hello world")
            mock_engine.runAndWait.assert_called_once()

    def test_speak_async(self):
        """异步朗读 / Async speak."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.speak("Hello async", blocking=False)
            assert result["success"] is True
            mock_engine.say.assert_called_with("Hello async")

    def test_speak_empty_text(self):
        """空文本朗读 / Empty text speak."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.speak("", blocking=True)
            assert result["success"] is False
            assert "empty" in result["error"].lower()

    def test_set_voice(self):
        """设置语音 / Set voice."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.set_voice("com.apple.speech.synthesis.voice.samantha")
            assert result["success"] is True

    def test_set_rate(self):
        """设置语速 / Set rate."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.set_rate(250)
            assert result["success"] is True
            assert tts.config.voice_rate == 250

    def test_set_volume(self):
        """设置音量 / Set volume."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.set_volume(0.5)
            assert result["success"] is True
            assert tts.config.voice_volume == 0.5

    def test_set_volume_clamped(self):
        """音量限制 0~1 / Volume clamped 0-1."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            tts.set_volume(2.0)
            assert tts.config.voice_volume <= 1.0
            tts.set_volume(-1.0)
            assert tts.config.voice_volume >= 0.0

    def test_stop(self):
        """停止播放 / Stop playback."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.stop()
            assert result["success"] is True
            mock_engine.stop.assert_called_once()

    def test_speak_multiple(self):
        """多段朗读 / Multiple texts."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            tts = TextToSpeech()
            result = tts.speak_multiple(["Hello", "World"], delay=0.0)
            assert result["success"] is True
            assert len(result["results"]) == 2


# ══════════════════════════════════════════════════════════════
# Conversation Tests / 对话测试
# ══════════════════════════════════════════════════════════════


class TestConversation:
    """对话引擎单元测试 / Conversation engine unit tests."""

    @pytest.fixture
    def mock_components(self):
        """模拟 STT 和 TTS / Mock STT and TTS."""
        stt = MagicMock(spec=SpeechToText)
        tts = MagicMock(spec=TextToSpeech)
        return stt, tts

    def test_initial_state(self, mock_components):
        """初始状态 / Initial state."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        assert conv.state == ConversationState.IDLE
        assert conv.is_running is False

    def test_state_transition(self, mock_components):
        """状态转换 / State transition."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        conv.state = ConversationState.LISTENING
        assert conv.state == ConversationState.LISTENING
        conv.state = ConversationState.PROCESSING
        assert conv.state == ConversationState.PROCESSING

    def test_state_history(self, mock_components):
        """状态历史记录 / State history."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        conv.state = ConversationState.LISTENING
        conv.state = ConversationState.PROCESSING
        conv.state = ConversationState.SPEAKING
        history = conv.state_history
        assert len(history) >= 3
        assert history[0]["from"] == "idle"
        assert history[0]["to"] == "listening"

    def test_process_command_with_callback(self, mock_components):
        """使用回调处理指令 / Process command with callback."""
        stt, tts = mock_components

        def understand(text):
            return f"You said: {text}"

        conv = Conversation(
            stt=stt, tts=tts,
            understand_callback=understand,
        )
        result = conv.process_command("hello")
        assert result["success"] is True
        assert result["response"] == "You said: hello"

    def test_process_command_default_callback(self, mock_components):
        """默认回调处理指令 / Process command with default callback."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        result = conv.process_command("test")
        assert result["success"] is True
        assert "heard" in result["response"].lower()

    def test_process_command_error(self, mock_components):
        """指令处理错误 / Command processing error."""
        stt, tts = mock_components

        def broken_callback(text):
            raise ValueError("Something broke")

        conv = Conversation(
            stt=stt, tts=tts,
            understand_callback=broken_callback,
        )
        result = conv.process_command("hello")
        assert result["success"] is False
        assert "error" in result

    def test_set_understand_callback(self, mock_components):
        """设置理解回调 / Set understand callback."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)

        def my_callback(text):
            return f"Echo: {text}"

        conv.set_understand_callback(my_callback)
        result = conv.process_command("hi")
        assert result["response"] == "Echo: hi"

    def test_run_cycle_no_wake_word(self, mock_components):
        """无唤醒词的完整循环 / Full cycle without wake word."""
        stt, tts = mock_components
        stt.listen_with_retry.return_value = {
            "success": True,
            "text": "hello world",
            "error": None,
        }
        tts.speak.return_value = {"success": True, "error": None}

        conv = Conversation(stt=stt, tts=tts)
        result = conv.run_cycle(require_wake_word=False)

        assert result["success"] is True
        assert result["input"] == "hello world"
        assert result["wake_word_used"] is False
        stt.listen_with_retry.assert_called_once()

    @patch.object(Conversation, "wait_for_wake_word")
    def test_run_cycle_with_wake_word(self, mock_wake, mock_components):
        """带唤醒词的完整循环 / Full cycle with wake word."""
        stt, tts = mock_components
        mock_wake.return_value = {
            "success": True,
            "wake_word": "hey atlas",
            "text": "hey atlas what's the weather",
            "error": None,
        }
        tts.speak.return_value = {"success": True, "error": None}

        conv = Conversation(stt=stt, tts=tts)
        result = conv.run_cycle(require_wake_word=True)

        assert result["success"] is True
        assert result["wake_word_used"] is True
        assert "weather" in result["input"]

    @patch.object(Conversation, "wait_for_wake_word")
    def test_run_cycle_wake_word_only(self, mock_wake, mock_components):
        """只说唤醒词（无后续指令）/
        Only wake word (no follow-up command)."""
        stt, tts = mock_components
        mock_wake.return_value = {
            "success": True,
            "wake_word": "hey atlas",
            "text": "hey atlas",
            "error": None,
        }
        tts.speak.return_value = {"success": True, "error": None}

        conv = Conversation(stt=stt, tts=tts)
        result = conv.run_cycle(require_wake_word=True)

        assert result["success"] is True
        assert result["response"] == "Yes? How can I help you?"

    def test_run_cycle_listen_failure(self, mock_components):
        """听取失败 / Listen failure."""
        stt, tts = mock_components
        stt.listen_with_retry.return_value = {
            "success": False,
            "text": None,
            "error": "No speech detected",
        }

        conv = Conversation(stt=stt, tts=tts)
        result = conv.run_cycle(require_wake_word=False)

        assert result["success"] is False

    def test_stats_tracking(self, mock_components):
        """统计跟踪 / Stats tracking."""
        stt, tts = mock_components
        stt.listen_with_retry.return_value = {
            "success": True,
            "text": "test",
            "error": None,
        }
        tts.speak.return_value = {"success": True, "error": None}

        conv = Conversation(stt=stt, tts=tts)
        conv.run_cycle(require_wake_word=False)

        assert conv.stats["total_cycles"] == 1
        assert conv.stats["successful_cycles"] == 1

    def test_reset_stats(self, mock_components):
        """重置统计 / Reset stats."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        conv.stats["total_cycles"] = 42
        conv.reset_stats()
        assert conv.stats["total_cycles"] == 0

    def test_start_stop_loop(self, mock_components):
        """启动和停止对话循环 / Start and stop conversation loop."""
        stt, tts = mock_components
        stt.listen_with_retry.return_value = {
            "success": True,
            "text": "test",
            "error": None,
        }
        tts.speak.return_value = {"success": True, "error": None}

        conv = Conversation(stt=stt, tts=tts)
        conv.start_loop(require_wake_word=False)
        time.sleep(0.2)
        assert conv.is_running is True

        result = conv.stop_loop(timeout=5.0)
        assert result["success"] is True
        assert conv.is_running is False

    def test_get_status(self, mock_components):
        """获取状态 / Get status."""
        stt, tts = mock_components
        conv = Conversation(stt=stt, tts=tts)
        status = conv.get_status()
        assert status["state"] == "idle"
        assert "config" in status
        assert "stats" in status


# ══════════════════════════════════════════════════════════════
# Integration-Style Tests / 集成风格测试
# ══════════════════════════════════════════════════════════════


class TestVoiceConfigIntegration:
    """配置与组件集成测试 / Config and component integration."""

    def test_config_propagates_to_components(self):
        """配置传播到子组件 / Config propagates to sub-components."""
        config = VoiceConfig(
            wake_words=["computer"],
            language="en-US",
            voice_rate=200,
        )
        stt = SpeechToText(config)
        tts = TextToSpeech(config)
        conv = Conversation(stt=stt, tts=tts, config=config)

        assert conv.config.language == "en-US"
        assert "computer" in conv.wake_detector.phrases
        assert conv.config.voice_rate == 200

    def test_wake_detector_from_config(self):
        """从配置创建唤醒词检测器 /
        Wake detector created from config."""
        config = VoiceConfig(wake_words=["hey atlas", "computer"])
        conv = Conversation(config=config)
        assert "computer" in conv.wake_detector.phrases
        assert "hey atlas" in conv.wake_detector.phrases


if __name__ == "__main__":
    pytest.main(["-v", __file__])
