/* Atlas — Chat Module
   消息发送、泡泡渲染、SSE 流式接入、语音输入 */

const AtlasChat = (() => {
  /* 状态 */
  const state = {
    streaming: false,
    sessionId: null,
    listening: false,
    recognition: null,
    voiceInput: localStorage.getItem('atlas-voice-input') !== 'false',
    tts: localStorage.getItem('atlas-tts') !== 'false',
  };

  /* 发送消息 */
  async function send(text) {
    if (!text || !text.trim() || state.streaming) return;
    const msg = text.trim();

    addBubble(msg, 'user');
    document.getElementById('consoleInput').value = '';
    state.streaming = true;
    setStreamStatus('🟡 思考中');

    const sessionId = 'web_' + Date.now().toString(36);
    state.sessionId = sessionId;

    let fullResponse = '';
    let streamPhase = '';

    AtlasAPI.chatStream(msg, sessionId, {
      onEvent(eventType, data) {
        switch (eventType) {
          case 'message_received':
            break;
          case 'intent_analyzing':
            addStream('🧠 意图路由...');
            break;
          case 'intent_result':
            addStream(`🎯 ${data.intent} (${(data.confidence * 100).toFixed(0)}%)`);
            break;
          case 'memory_recalling':
            addStream('📡 记忆检索...');
            break;
          case 'memory_result':
            addStream(`💾 召回 ${data.count} 条记忆`);
            break;
          case 'stream_start':
            streamPhase = 'responding';
            break;
          case 'stream_chunk':
            fullResponse += data.text || '';
            // 实时更新气泡内容
            const bubble = document.querySelector('.chat-bubble:last-child .bubble-text');
            if (bubble && bubble.dataset.role === 'assistant') {
              bubble.textContent = fullResponse;
            }
            break;
          case 'response':
            // 完成
            break;
          case 'error':
            fullResponse += `\n\n[错误: ${data.message}]`;
            break;
        }
      },
      onDone() {
        state.streaming = false;
        setStreamStatus('🟢 就绪');
        if (fullResponse) {
          addBubble(fullResponse, 'assistant');
        }
      },
      onError(err) {
        state.streaming = false;
        setStreamStatus('🔴 错误');
        // fallback: 使用同步 API
        fallbackChat(msg);
      },
    });
  }

  /* 降级到同步 API */
  async function fallbackChat(msg) {
    try {
      const r = await AtlasAPI.post('/api/chat', { message: msg });
      addBubble(r.response, 'assistant');
      setStreamStatus('🟢 就绪');
    } catch (e) {
      addBubble(`连接失败: ${e.message}`, 'error');
      setStreamStatus('🔴 错误');
    }
  }

  /* 添加消息气泡 */
  function addBubble(text, role) {
    const layer = document.getElementById('chatLayer');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.dataset.role = role;

    const avatar = document.createElement('span');
    avatar.className = 'bubble-avatar';
    avatar.textContent = role === 'user' ? '👤' : '◆';
    bubble.appendChild(avatar);

    const content = document.createElement('div');
    content.className = 'bubble-content';

    const textEl = document.createElement('div');
    textEl.className = 'bubble-text';
    textEl.textContent = text;
    content.appendChild(textEl);

    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' });
    const meta = document.createElement('div');
    meta.className = 'bubble-meta';
    meta.textContent = time;
    content.appendChild(meta);

    bubble.appendChild(content);
    layer.appendChild(bubble);
    layer.scrollTop = layer.scrollHeight;

    // 清理旧气泡
    while (layer.children.length > 50) {
      layer.firstChild.remove();
    }
  }

  /* 设置流式状态文本 */
  function setStreamStatus(text) {
    const el = document.querySelector('.console-stream-status');
    if (el) el.textContent = text;
  }

  /* 初始化语音识别 */
  function initVoice(voiceBtn) {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      if (voiceBtn) voiceBtn.style.display = 'none';
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SR();
    state.recognition.lang = 'zh-CN';
    state.recognition.continuous = false;
    state.recognition.interimResults = false;
    state.recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      send(transcript);
      if (voiceBtn) voiceBtn.textContent = '🎤';
    };
    state.recognition.onend = () => {
      if (voiceBtn) voiceBtn.textContent = '🎤';
      state.listening = false;
    };
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        if (!state.voiceInput) return;
        if (state.listening) { state.recognition.stop(); return; }
        state.recognition.start();
        voiceBtn.textContent = '🔴';
        state.listening = true;
      });
    }
  }

  return { send, addBubble, initVoice, setStreamStatus };
})();
