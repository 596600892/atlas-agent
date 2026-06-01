# Atlas Phase 3: Voice Engine 在线升级

## 目标
将 Voice Engine 从纯离线提升为"在线优先，离线回退"的混合引擎。

## 变更清单

### 1. VoiceConfig 新增字段
- `stt_engine: str = "google"` — "google" | "whisper"
- `whisper_model: str = "whisper-1"` — OpenAI Whisper 模型名
- `whisper_api_key: Optional[str] = None` — API key（None=走OPENAI_API_KEY环境变量）
- `tts_save_dir: Optional[str] = None` — TTS文件保存目录

### 2. SpeechToText — Whisper API 支持
- 新增 `_recognize_whisper(audio)` 私有方法
- `listen()` 根据 `stt_engine` 选择识别引擎
- Whisper 失败时自动降级到 Google（带warning日志）
- 音频数据临时保存为 WAV 再发送到 Whisper API

### 3. TextToSpeech — 文件输出 + 预设
- 新增 `save_to_file(text, filepath)` — 使用系统 `say` 命令（macOS）生成 AIFF 音频文件
- 新增 `PRESETS` 类常量和 `get_preset(name)` 类方法

### 4. 测试扩展
- Mock Whisper API 路径（3个测试：成功/失败/降级）
- TTS save_to_file 测试
- 新增 `stt_engine="whisper"` 配置测试

### 5. CLI + setup.py 更新
- CLI `atlas voice` 子命令添加 `--engine` 参数
- setup.py 添加 `extras_require["voice_online"] = ["openai>=1.0"]`
