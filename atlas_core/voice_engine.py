#!/usr/bin/env python3
"""
Atlas Voice Engine — 语音引擎
===================================

完整语音交互模块：语音识别 (STT) + 语音合成 (TTS) + 对话管理 + 唤醒词检测。
Complete voice interaction module: Speech-to-Text + Text-to-Speech + Conversation + Wake word.

Dependencies: SpeechRecognition, pyttsx3, pyaudio
Works on macOS with a microphone.
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("atlas.voice_engine")

# ══════════════════════════════════════════════════════════════
# Config / 配置
# ══════════════════════════════════════════════════════════════


@dataclass
class VoiceConfig:
    """语音引擎配置 / Voice engine configuration"""
    # Microphone / 麦克风
    mic_index: Optional[int] = None       # None = 系统默认麦克风 / system default
    energy_threshold: int = 3000           # 环境噪音阈值 / ambient noise threshold
    pause_threshold: float = 0.8           # 静音多久算一句话结束 / silence = end of phrase
    dynamic_energy: bool = True            # 自动调整噪音阈值 / auto-adjust threshold
    phrase_time_limit: float = 10.0        # 最长录音秒数 / max recording seconds

    # Speech recognition / 语音识别
    language: str = "zh-CN"                # 识别语言 / recognition language (zh-CN, en-US, etc.)
    timeout: float = 5.0                   # 等待说话的超时秒数 / wait timeout for speech
    retry_on_failure: int = 2              # 失败重试次数 / retries on failure

    # Wake word / 唤醒词
    wake_words: list[str] = field(default_factory=lambda: ["hey atlas", "atlas", "hello atlas"])
    wake_word_required: bool = True        # 是否需要唤醒词 / require wake word

    # TTS / 语音合成
    voice_rate: int = 180                  # 语速 (words per minute) / speech rate
    voice_volume: float = 1.0             # 音量 0.0~1.0 / volume
    voice_id: Optional[str] = None         # None = 系统默认语音 / system default voice


# ══════════════════════════════════════════════════════════════
# Speech Recognition / 语音识别
# ══════════════════════════════════════════════════════════════


class SpeechToText:
    """
    Speech-to-Text using speech_recognition library.
    使用 speech_recognition 库进行语音识别。

    Supports Google Web Speech API (offline fallback via recognize_sphinx optional).
    支持 Google Web Speech API。
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        """
        初始化语音识别器 / Initialize speech recognizer.

        Args:
            config: 语音配置，None时使用默认 / voice config, uses defaults if None
        """
        self.config = config or VoiceConfig()
        self._recognizer = None  # 延迟初始化 / lazy init
        self._microphone = None
        self._initialized = False
        self._init_error: Optional[str] = None

    def _lazy_init(self) -> bool:
        """
        延迟初始化识别器和麦克风 / Lazy-init recognizer and microphone.

        Returns:
            True 如果初始化成功 / True if initialization succeeded
        """
        if self._initialized:
            return True

        try:
            import speech_recognition as sr

            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.config.energy_threshold
            self._recognizer.pause_threshold = self.config.pause_threshold
            self._recognizer.dynamic_energy_threshold = self.config.dynamic_energy

            # 获取麦克风 / get microphone
            if self.config.mic_index is not None:
                self._microphone = sr.Microphone(device_index=self.config.mic_index)
            else:
                self._microphone = sr.Microphone()

            # 调整环境噪音 / calibrate for ambient noise
            logger.info("Calibrating microphone for ambient noise...")
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
            logger.info(
                f"Microphone calibrated. Energy threshold: "
                f"{self._recognizer.energy_threshold}"
            )

            self._initialized = True
            return True

        except ImportError as e:
            self._init_error = (
                f"Missing dependency: speech_recognition. "
                f"Install with: pip install SpeechRecognition pyaudio. Error: {e}"
            )
            logger.error(self._init_error)
            return False
        except OSError as e:
            self._init_error = (
                f"Microphone not available or inaccessible: {e}. "
                f"Check your audio input devices."
            )
            logger.error(self._init_error)
            return False
        except Exception as e:
            self._init_error = f"Unexpected error during STT init: {e}"
            logger.error(self._init_error)
            return False

    def list_microphones(self) -> list[dict]:
        """
        列出所有可用麦克风 / List all available microphones.

        Returns:
            list[dict]: 每个麦克风的 {index, name, channels, sample_rate}
                        / each mic's info dict

        Raises:
            RuntimeError: 如果 speech_recognition 未安装
                          / if speech_recognition is not installed
        """
        try:
            import speech_recognition as sr
        except ImportError as e:
            raise RuntimeError(f"speech_recognition not installed: {e}")

        mics = sr.Microphone.list_microphone_names()
        result = []
        for i, name in enumerate(mics):
            try:
                mic = sr.Microphone(device_index=i)
                result.append({
                    "index": i,
                    "name": name,
                    "sample_rate": mic.SAMPLE_RATE,
                    "sample_width": mic.SAMPLE_WIDTH,
                })
            except Exception:
                result.append({"index": i, "name": name, "error": "could not open"})
        return result

    def listen(self, timeout: Optional[float] = None) -> dict:
        """
        从麦克风听取语音 / Listen for speech from microphone.

        Args:
            timeout: 覆盖配置的超时 / override config timeout (seconds)

        Returns:
            dict: {
                "success": bool,
                "text": str | None,
                "confidence": float | None,
                "error": str | None,
                "raw_duration": float,
            }
        """
        result = {
            "success": False,
            "text": None,
            "confidence": None,
            "error": None,
            "raw_duration": 0.0,
        }

        if not self._lazy_init():
            result["error"] = self._init_error or "STT initialization failed"
            return result

        timeout = timeout if timeout is not None else self.config.timeout

        try:
            logger.info(f"Listening (timeout={timeout}s, lang={self.config.language})...")

            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=self.config.phrase_time_limit,
                )

            result["raw_duration"] = len(audio.frame_data) / (
                audio.sample_rate * audio.sample_width
            )

            # 使用 Google Web Speech API 进行识别
            # Using Google Web Speech API for recognition
            try:
                text = self._recognizer.recognize_google(
                    audio, language=self.config.language
                )
                result["success"] = True
                result["text"] = text
                result["confidence"] = 1.0  # Google API 不返回置信度 / doesn't return confidence
                logger.info(f"Recognized: \"{text}\"")
            except LookupError:
                # 语音无法理解 / speech was unintelligible
                result["error"] = "Speech unintelligible"
                logger.warning("Speech was unintelligible")
            except Exception as e:
                result["error"] = f"Recognition failed: {e}"
                logger.error(f"Recognition error: {e}")

        except queue.Empty:
            # 超时 — 没有说话 / timeout — no speech detected
            result["error"] = "Silence timeout — no speech detected"
            logger.info("Silence timeout — no speech detected")
        except OSError as e:
            result["error"] = f"Microphone error: {e}"
            logger.error(f"Microphone error: {e}")
        except Exception as e:
            result["error"] = f"Unexpected listen error: {e}"
            logger.error(f"Unexpected listen error: {e}")

        return result

    def listen_with_retry(self, timeout: Optional[float] = None) -> dict:
        """
        带重试的语音听取 / Listen with automatic retries.

        Args:
            timeout: 每次尝试的超时 / timeout per attempt

        Returns:
            dict: 同 listen() / same as listen()
        """
        max_retries = self.config.retry_on_failure
        last_result = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries}")
                time.sleep(0.5)

            last_result = self.listen(timeout=timeout)
            if last_result["success"]:
                return last_result
            # 如果是硬件错误，不要重试 / don't retry on hardware errors
            if last_result.get("error") and any(
                kw in (last_result["error"] or "").lower()
                for kw in ["microphone", "not installed", "import"]
            ):
                return last_result

        return last_result or {"success": False, "error": "All retries exhausted"}


# ══════════════════════════════════════════════════════════════
# Text-to-Speech / 语音合成
# ══════════════════════════════════════════════════════════════


class TextToSpeech:
    """
    Text-to-Speech using pyttsx3 (offline, cross-platform).
    使用 pyttsx3 进行离线语音合成。

    Works offline, Mac/Win/Linux compatible.
    离线可用，兼容 Mac/Win/Linux。
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        """
        初始化 TTS 引擎 / Initialize TTS engine.

        Args:
            config: 语音配置 / voice configuration
        """
        self.config = config or VoiceConfig()
        self._engine = None
        self._initialized = False
        self._init_error: Optional[str] = None
        self._voices: list[dict] = []

    def _lazy_init(self) -> bool:
        """延迟初始化 TTS 引擎 / Lazy-init TTS engine."""
        if self._initialized:
            return True

        try:
            import pyttsx3

            self._engine = pyttsx3.init(driverName=None)  # 自动选择驱动 / auto-select driver
            self._engine.setProperty("rate", self.config.voice_rate)
            self._engine.setProperty("volume", self.config.voice_volume)

            # 设置语音 / set voice
            if self.config.voice_id:
                self._engine.setProperty("voice", self.config.voice_id)

            # 获取可用语音列表 / get available voices
            try:
                voices = self._engine.getProperty("voices")
                self._voices = [
                    {
                        "id": v.id,
                        "name": v.name,
                        "languages": v.languages if hasattr(v, "languages") else [],
                    }
                    for v in voices
                ]
            except Exception:
                self._voices = []

            self._initialized = True
            logger.info(f"TTS initialized. Rate={self.config.voice_rate}, "
                        f"Volume={self.config.voice_volume}, "
                        f"Available voices: {len(self._voices)}")
            return True

        except ImportError as e:
            self._init_error = (
                f"Missing dependency: pyttsx3. "
                f"Install with: pip install pyttsx3. Error: {e}"
            )
            logger.error(self._init_error)
            return False
        except Exception as e:
            self._init_error = f"TTS init failed: {e}"
            logger.error(self._init_error)
            return False

    @property
    def is_available(self) -> bool:
        """引擎是否可用 / Whether the engine is available."""
        return self._lazy_init()

    @property
    def voices(self) -> list[dict]:
        """可用语音列表 / Available voices list."""
        self._lazy_init()
        return self._voices

    def set_voice(self, voice_id: str) -> dict:
        """
        设置语音 / Set voice by ID.

        Args:
            voice_id: 语音ID (如 'com.apple.speech.synthesis.voice.samantha')

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        if not self._lazy_init():
            return {"success": False, "error": self._init_error}
        try:
            self._engine.setProperty("voice", voice_id)
            self.config.voice_id = voice_id
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_rate(self, rate: int) -> dict:
        """
        设置语速 / Set speech rate.

        Args:
            rate: 语速 (words per minute, 通常 100-300)

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        if not self._lazy_init():
            return {"success": False, "error": self._init_error}
        try:
            self._engine.setProperty("rate", rate)
            self.config.voice_rate = rate
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_volume(self, volume: float) -> dict:
        """
        设置音量 / Set volume.

        Args:
            volume: 音量 0.0~1.0

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        if not self._lazy_init():
            return {"success": False, "error": self._init_error}
        try:
            clamped_volume = max(0.0, min(1.0, volume))
            self._engine.setProperty("volume", clamped_volume)
            self.config.voice_volume = clamped_volume
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def speak(self, text: str, blocking: bool = True) -> dict:
        """
        将文本转为语音并播放 / Speak the given text aloud.

        Args:
            text: 要朗读的文本 / text to speak
            blocking: True=等待播放完成 / wait for completion
                      False=异步播放 / async (non-blocking)

        Returns:
            dict: {
                "success": bool,
                "error": str | None,
                "text": str,
                "blocking": bool,
            }
        """
        result = {
            "success": False,
            "error": None,
            "text": text,
            "blocking": blocking,
        }

        if not text or not text.strip():
            result["error"] = "Empty text — nothing to speak"
            return result

        if not self._lazy_init():
            result["error"] = self._init_error
            return result

        try:
            self._engine.say(text)

            if blocking:
                self._engine.runAndWait()
                result["success"] = True
            else:
                # 异步：在后台线程中播放 / async: play in background thread
                def _speak_async():
                    try:
                        self._engine.runAndWait()
                    except Exception as e:
                        logger.error(f"Async speak error: {e}")

                thread = threading.Thread(target=_speak_async, daemon=True)
                thread.start()
                result["success"] = True

            logger.info(f"TTS {'spoken' if blocking else 'queued'}: \"{text[:60]}...\" "
                        f"({len(text)} chars)")
            return result

        except RuntimeError as e:
            # pyttsx3 可能因为 run loop 问题抛出 / pyttsx3 run loop issues
            result["error"] = f"TTS runtime error: {e}"
            logger.error(result["error"])
            return result
        except Exception as e:
            result["error"] = f"TTS speak error: {e}"
            logger.error(result["error"])
            return result

    def speak_multiple(self, texts: list[str], delay: float = 0.3) -> dict:
        """
        依次朗读多条文本 / Speak multiple texts sequentially.

        Args:
            texts: 文本列表 / list of text strings
            delay: 文本之间的间隔秒数 / delay between texts (seconds)

        Returns:
            dict: {"success": bool, "results": list[dict], "error": str | None}
        """
        if not self._lazy_init():
            return {"success": False, "results": [], "error": self._init_error}

        results = []
        all_ok = True
        for i, text in enumerate(texts):
            if i > 0 and delay > 0:
                time.sleep(delay)
            r = self.speak(text, blocking=True)
            results.append(r)
            if not r["success"]:
                all_ok = False

        return {"success": all_ok, "results": results, "error": None}

    def stop(self) -> dict:
        """
        停止当前播放 / Stop current playback.

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        if not self._lazy_init():
            return {"success": False, "error": self._init_error}
        try:
            self._engine.stop()
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# Wake Word Detection / 唤醒词检测
# ══════════════════════════════════════════════════════════════


class WakeWordDetector:
    """
    唤醒词检测器（纯本地，无需云端）/
    Wake word detector (fully local, no cloud).

    通过检测语音识别结果中是否包含唤醒关键词来工作。
    Works by checking if recognized speech contains wake keywords.
    """

    def __init__(self, wake_words: Optional[list[str]] = None):
        """
        初始化唤醒词检测器 / Initialize wake word detector.

        Args:
            wake_words: 唤醒词列表，默认 ["hey atlas", "atlas", "hello atlas"]
                        / list of wake phrases
        """
        self.wake_words = [w.lower().strip() for w in (wake_words or [])]
        if not self.wake_words:
            self.wake_words = ["hey atlas", "atlas", "hello atlas"]
        self._last_detected: Optional[str] = None
        self._detection_count = 0

    @property
    def phrases(self) -> list[str]:
        """当前唤醒词列表 / Current wake phrases."""
        return list(self.wake_words)

    def add_wake_word(self, phrase: str) -> None:
        """添加额外唤醒词 / Add a wake word phrase."""
        p = phrase.lower().strip()
        if p and p not in self.wake_words:
            self.wake_words.append(p)

    def contains_wake_word(self, text: str) -> dict:
        """
        检测文本中是否包含唤醒词 / Check if text contains a wake word.

        Args:
            text: 要检测的文本 / text to check

        Returns:
            dict: {
                "detected": bool,
                "wake_word": str | None,      # 匹配到的唤醒词
                "confidence": float,           # 0.0 ~ 1.0
                "text_lower": str,             # 小写文本 / lowercased text
            }
        """
        if not text:
            return {
                "detected": False,
                "wake_word": None,
                "confidence": 0.0,
                "text_lower": "",
            }

        text_lower = text.lower().strip()
        # 按长度降序匹配，优先匹配最长的唤醒词（如 "hello atlas" 优先于 "atlas"）
        # Match longer wake words first (e.g. "hello atlas" before "atlas")
        sorted_wake_words = sorted(self.wake_words, key=len, reverse=True)
        for ww in sorted_wake_words:
            if ww in text_lower:
                # 计算粗略置信度：精确匹配 = 1.0, 子串匹配 = 0.8
                # Calculate rough confidence: exact match = 1.0, substring = 0.8
                confidence = 1.0 if text_lower == ww else 0.8
                self._last_detected = ww
                self._detection_count += 1
                return {
                    "detected": True,
                    "wake_word": ww,
                    "confidence": confidence,
                    "text_lower": text_lower,
                }

        return {
            "detected": False,
            "wake_word": None,
            "confidence": 0.0,
            "text_lower": text_lower,
        }

    def strip_wake_word(self, text: str) -> str:
        """
        从文本中移除唤醒词前缀 / Remove wake word prefix from text.

        "hey atlas what's the weather" → "what's the weather"

        Args:
            text: 原始文本 / original text

        Returns:
            str: 去掉唤醒词后的文本 / text without wake word
        """
        if not text:
            return ""

        text_lower = text.lower().strip()
        for ww in sorted(self.wake_words, key=len, reverse=True):
            if text_lower.startswith(ww):
                remainder = text[len(ww):].strip()
                # 去掉开头的标点/空格 / strip leading punctuation/whitespace
                while remainder and remainder[0] in ",.?!，。？！ ":
                    remainder = remainder[1:]
                return remainder
            # 也检查中间位置 / also check mid-text
            idx = text_lower.find(ww)
            if idx >= 0:
                before = text[:idx].strip()
                after = text[idx + len(ww):].strip()
                if not before:  # 唤醒词在开头 / wake word at start
                    return after
        return text

    @property
    def stats(self) -> dict:
        """检测统计信息 / Detection statistics."""
        return {
            "total_detections": self._detection_count,
            "last_detected": self._last_detected,
            "wake_words": self.wake_words,
        }


# ══════════════════════════════════════════════════════════════
# Conversation State / 对话状态
# ══════════════════════════════════════════════════════════════


class ConversationState(Enum):
    """对话状态机状态 / Conversation state machine states."""
    IDLE = "idle"                    # 等待唤醒 / waiting for wake word
    LISTENING = "listening"          # 听取用户指令 / listening for command
    PROCESSING = "processing"        # 理解并生成回复 / understanding + generating response
    SPEAKING = "speaking"            # 朗读回复 / speaking response
    PAUSED = "paused"                # 手动暂停 / manually paused
    ERROR = "error"                  # 错误状态 / error state


# ══════════════════════════════════════════════════════════════
# Conversation Loop / 对话循环
# ══════════════════════════════════════════════════════════════


class Conversation:
    """
    完整的对话循环：listen → understand → respond → speak /
    Complete conversation loop: listen → understand → respond → speak.

    支持唤醒词激活、超时处理、错误恢复。
    Supports wake word activation, timeout handling, error recovery.
    """

    def __init__(
        self,
        stt: Optional[SpeechToText] = None,
        tts: Optional[TextToSpeech] = None,
        config: Optional[VoiceConfig] = None,
        understand_callback: Optional[Callable[[str], str]] = None,
    ):
        """
        初始化对话引擎 / Initialize conversation engine.

        Args:
            stt: 语音识别器 / speech-to-text instance
            tts: 语音合成器 / text-to-speech instance
            config: 语音配置 / voice configuration
            understand_callback: 理解回调，接收文本返回回复 /
                understanding callback, receives text returns response
        """
        self.config = config or VoiceConfig()
        self.stt = stt or SpeechToText(self.config)
        self.tts = tts or TextToSpeech(self.config)
        self.wake_detector = WakeWordDetector(self.config.wake_words)

        # 理解回调 / understanding callback
        self._understand_callback = understand_callback

        # 状态管理 / state management
        self._state = ConversationState.IDLE
        self._state_history: list[dict] = []
        self._should_stop = threading.Event()
        self._loop_thread: Optional[threading.Thread] = None

        # 对话统计 / conversation statistics
        self.stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "wake_word_triggers": 0,
            "total_listen_time": 0.0,
        }

        logger.info("Conversation engine initialized")

    # ── State Management / 状态管理 ──────────────────────────

    @property
    def state(self) -> ConversationState:
        """当前对话状态 / Current conversation state."""
        return self._state

    @state.setter
    def state(self, new_state: ConversationState) -> None:
        """
        设置状态并记录历史 / Set state and record history.

        Args:
            new_state: 新状态 / new state
        """
        old_state = self._state
        self._state = new_state
        entry = {
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": time.time(),
        }
        self._state_history.append(entry)
        # 只保留最近100条 / keep only last 100 entries
        if len(self._state_history) > 100:
            self._state_history = self._state_history[-100:]
        logger.debug(f"State: {old_state.value} → {new_state.value}")

    @property
    def state_history(self) -> list[dict]:
        """状态变更历史 / State change history."""
        return list(self._state_history)

    # ── Wake Word / 唤醒词 ──────────────────────────────────

    def wait_for_wake_word(self, timeout: Optional[float] = None) -> dict:
        """
        等待用户说出唤醒词 / Wait for user to say the wake word.

        循环 listen() 直到检测到唤醒词或超时。
        Loops listen() until wake word detected or timeout.

        Args:
            timeout: 总超时秒数，None=无限 /
                    total timeout in seconds, None=infinite

        Returns:
            dict: {
                "success": bool,        # True=检测到唤醒词
                "wake_word": str|None,  # 匹配的唤醒词
                "text": str,            # 识别的原始文本
                "error": str|None,
            }
        """
        self.state = ConversationState.LISTENING
        start_time = time.time()

        while not self._should_stop.is_set():
            # 检查总超时 / check total timeout
            if timeout is not None and (time.time() - start_time) > timeout:
                self.state = ConversationState.IDLE
                return {
                    "success": False,
                    "wake_word": None,
                    "text": "",
                    "error": "Wake word timeout",
                }

            # 听取语音 / listen for speech
            result = self.stt.listen(timeout=self.config.timeout)

            if not result["success"]:
                # 超时或无声 — 继续等待 / timeout or silence — keep waiting
                if "timeout" in (result.get("error") or "").lower():
                    continue
                # 硬件错误 — 返回 / hardware error — bail out
                return {
                    "success": False,
                    "wake_word": None,
                    "text": "",
                    "error": result.get("error"),
                }

            # 检测唤醒词 / check for wake word
            text = result.get("text", "")
            ww_result = self.wake_detector.contains_wake_word(text)

            if ww_result["detected"]:
                self.stats["wake_word_triggers"] += 1
                logger.info(f"Wake word detected: '{ww_result['wake_word']}' "
                            f"(confidence={ww_result['confidence']})")
                self.state = ConversationState.IDLE
                return {
                    "success": True,
                    "wake_word": ww_result["wake_word"],
                    "text": text,
                    "error": None,
                }

        # 被 stop() 中断 / interrupted by stop()
        self.state = ConversationState.IDLE
        return {"success": False, "wake_word": None, "text": "",
                "error": "Conversation stopped"}

    # ── Core Loop / 核心循环 ────────────────────────────────

    def set_understand_callback(self, callback: Callable[[str], str]) -> None:
        """
        设置理解回调 / Set the understanding callback.

        Args:
            callback: 接收用户文本，返回回复文本 /
                     receives user text, returns response text
        """
        self._understand_callback = callback

    def _default_understand(self, text: str) -> str:
        """
        默认理解回调（可被子类覆写）/
        Default understanding callback (override in subclass).

        Args:
            text: 用户说的话 / what the user said

        Returns:
            str: 回复文本 / response text
        """
        return f"I heard you say: \"{text}\". I am learning to respond better."

    def process_command(self, text: str) -> dict:
        """
        处理用户指令并返回回复 / Process user command and return response.

        Args:
            text: 用户文本 / user text

        Returns:
            dict: {
                "success": bool,
                "input": str,
                "response": str | None,
                "error": str | None,
                "processing_time": float,
            }
        """
        start = time.time()
        self.state = ConversationState.PROCESSING

        try:
            # 调用理解回调 / call understanding callback
            callback = self._understand_callback or self._default_understand
            response = callback(text)
            elapsed = time.time() - start

            result = {
                "success": True,
                "input": text,
                "response": response,
                "error": None,
                "processing_time": elapsed,
            }
            logger.info(f"Processed input ({elapsed:.3f}s): "
                        f"\"{text[:40]}...\" → \"{response[:40]}...\"")

            self.state = ConversationState.SPEAKING
            return result

        except Exception as e:
            elapsed = time.time() - start
            error_msg = f"Understanding error: {e}"
            logger.error(error_msg)

            self.state = ConversationState.ERROR
            return {
                "success": False,
                "input": text,
                "response": None,
                "error": error_msg,
                "processing_time": elapsed,
            }

    def run_cycle(self, require_wake_word: Optional[bool] = None) -> dict:
        """
        执行一个完整的对话循环 /
        Execute one complete conversation cycle.

        流程 / Flow:
        (可选唤醒) → listen(听取用户) → process(理解) → speak(回复)

        Args:
            require_wake_word: 是否要求唤醒词，None=使用配置 /
                              whether wake word is required, None=use config

        Returns:
            dict: {
                "success": bool,
                "wake_word_used": bool,
                "input": str | None,
                "response": str | None,
                "error": str | None,
                "cycle_time": float,
                "states": list[str],
            }
        """
        self.stats["total_cycles"] += 1
        start_time = time.time()
        cycle_states = []
        require_ww = (
            require_wake_word
            if require_wake_word is not None
            else self.config.wake_word_required
        )

        try:
            # ── 阶段 1: 唤醒 / Phase 1: Wake ────────────────
            input_text = None
            if require_ww:
                ww_result = self.wait_for_wake_word(timeout=self.config.timeout * 3)
                cycle_states.append("wake_check")
                if not ww_result["success"]:
                    self.stats["failed_cycles"] += 1
                    elapsed = time.time() - start_time
                    return {
                        "success": False,
                        "wake_word_used": True,
                        "input": None,
                        "response": None,
                        "error": ww_result.get("error", "Wake word not detected"),
                        "cycle_time": elapsed,
                        "states": cycle_states,
                    }
                # 从文本中去掉唤醒词 / strip wake word from text
                input_text = self.wake_detector.strip_wake_word(
                    ww_result.get("text", "")
                )
                if not input_text:
                    # 只说唤醒词，没有后续指令 /
                    # only said wake word, no command
                    self.state = ConversationState.SPEAKING
                    response = "Yes? How can I help you?"
                    self.tts.speak(response, blocking=True)
                    self.state = ConversationState.IDLE
                    elapsed = time.time() - start_time
                    return {
                        "success": True,
                        "wake_word_used": True,
                        "input": ww_result["text"],
                        "response": response,
                        "error": None,
                        "cycle_time": elapsed,
                        "states": cycle_states + ["listen", "process", "speak"],
                    }
            else:
                # 不需要唤醒词 — 直接听 / no wake word — listen directly
                self.state = ConversationState.LISTENING
                listen_result = self.stt.listen_with_retry(
                    timeout=self.config.timeout
                )
                cycle_states.append("listen")
                if not listen_result["success"]:
                    self.stats["failed_cycles"] += 1
                    elapsed = time.time() - start_time
                    self.state = ConversationState.IDLE
                    return {
                        "success": False,
                        "wake_word_used": False,
                        "input": None,
                        "response": None,
                        "error": listen_result.get("error", "Listen failed"),
                        "cycle_time": elapsed,
                        "states": cycle_states,
                    }
                input_text = listen_result.get("text", "")

            # ── 阶段 2: 理解 / Phase 2: Understand ──────────
            cycle_states.append("listen")
            if not input_text:
                self.stats["failed_cycles"] += 1
                elapsed = time.time() - start_time
                self.state = ConversationState.IDLE
                return {
                    "success": False,
                    "wake_word_used": require_ww,
                    "input": None,
                    "response": None,
                    "error": "No input text",
                    "cycle_time": elapsed,
                    "states": cycle_states,
                }

            process_result = self.process_command(input_text)
            cycle_states.append("process")

            if not process_result["success"]:
                self.stats["failed_cycles"] += 1
                elapsed = time.time() - start_time
                self.state = ConversationState.IDLE
                return {
                    "success": False,
                    "wake_word_used": require_ww,
                    "input": input_text,
                    "response": None,
                    "error": process_result.get("error", "Processing failed"),
                    "cycle_time": elapsed,
                    "states": cycle_states,
                }

            # ── 阶段 3: 回复 / Phase 3: Speak ───────────────
            response_text = process_result.get("response", "")
            speak_result = self.tts.speak(response_text, blocking=True)
            cycle_states.append("speak")

            if not speak_result["success"]:
                logger.warning(f"TTS speak returned error: "
                               f"{speak_result.get('error')}")

            elapsed = time.time() - start_time
            self.stats["successful_cycles"] += 1
            self.state = ConversationState.IDLE

            return {
                "success": True,
                "wake_word_used": require_ww,
                "input": input_text,
                "response": response_text,
                "error": None,
                "cycle_time": elapsed,
                "states": cycle_states,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.stats["failed_cycles"] += 1
            self.state = ConversationState.ERROR
            logger.error(f"Cycle error: {e}")
            return {
                "success": False,
                "wake_word_used": require_ww if require_ww is not None else False,
                "input": None,
                "response": None,
                "error": f"Cycle error: {e}",
                "cycle_time": elapsed,
                "states": cycle_states,
            }

    # ── Continuous Loop / 持续循环 ──────────────────────────

    def start_loop(
        self,
        require_wake_word: Optional[bool] = None,
        on_cycle_complete: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """
        在后台线程中启动持续对话循环 /
        Start continuous conversation loop in background thread.

        Args:
            require_wake_word: 是否需要唤醒词 / require wake word
            on_cycle_complete: 每轮循环完成后的回调 /
                               callback after each cycle completes
        """
        if self._loop_thread and self._loop_thread.is_alive():
            logger.warning("Conversation loop already running")
            return

        self._should_stop.clear()

        def _loop():
            logger.info("Conversation loop started (background)")
            while not self._should_stop.is_set():
                try:
                    result = self.run_cycle(require_wake_word=require_wake_word)
                    if on_cycle_complete:
                        on_cycle_complete(result)
                except Exception as e:
                    logger.error(f"Loop iteration error: {e}")
                    time.sleep(1)

            logger.info("Conversation loop stopped")

        self._loop_thread = threading.Thread(target=_loop, daemon=True)
        self._loop_thread.start()

    def stop_loop(self, timeout: float = 3.0) -> dict:
        """
        停止对话循环 / Stop the conversation loop.

        Args:
            timeout: 等待线程结束的超时 / timeout to wait for thread

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        self._should_stop.set()
        self.state = ConversationState.IDLE

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=timeout)
            if self._loop_thread.is_alive():
                return {
                    "success": False,
                    "error": "Loop thread did not stop within timeout",
                }

        self._loop_thread = None
        logger.info("Conversation loop stopped cleanly")
        return {"success": True, "error": None}

    @property
    def is_running(self) -> bool:
        """对话循环是否在运行 / Whether the loop is running."""
        return (
            self._loop_thread is not None and self._loop_thread.is_alive()
        )

    # ── Utility / 工具方法 ──────────────────────────────────

    def reset_stats(self) -> None:
        """重置对话统计 / Reset conversation statistics."""
        self.stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "wake_word_triggers": 0,
            "total_listen_time": 0.0,
        }

    def get_status(self) -> dict:
        """
        获取当前状态摘要 / Get current status summary.

        Returns:
            dict: 完整状态信息 / full status info
        """
        return {
            "state": self.state.value,
            "is_running": self.is_running,
            "stats": dict(self.stats),
            "config": {
                "wake_word_required": self.config.wake_word_required,
                "language": self.config.language,
                "voice_rate": self.config.voice_rate,
                "mic_index": self.config.mic_index,
                "wake_words": self.config.wake_words,
            },
            "wake_detector": self.wake_detector.stats,
            "state_history_count": len(self._state_history),
        }
