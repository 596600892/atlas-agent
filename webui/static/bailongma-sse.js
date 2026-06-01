/* Atlas — BaiLongma SSE Client (adapted)
   EventSource connection + event dispatch for Hermes API at localhost:8642
   All function names use _bl suffix to avoid conflicts with Atlas modules */

const BL_SSE = (() => {
  'use strict';

  const API_BASE = 'http://localhost:8642';

  // ── Connection state ──
  let _connected = false;

  // ── Path routing for two streams ──
  // L1 = user message processing; L2 = tick/heartbeat processing
  let _currentPath_bl = 'l2';

  // Safe access to stream panels (loaded separately as BL_Streams)
  function _getL1_bl() { return (window.BL_Streams || {}).L1; }
  function _getL2_bl() { return (window.BL_Streams || {}).L2; }
  function _currentStream_bl() {
    return _currentPath_bl === 'l1' ? _getL1_bl() : _getL2_bl();
  }
  // Fallback: dispatch CustomEvent so Atlas modules can react
  function _dispatchEvent_bl(type, data) {
    window.dispatchEvent(new CustomEvent('bl:' + type, { detail: data }));
  }

  // ── Token rate tracking ──
  let _tokenAccum_bl = 0;
  let _tokenWindow_bl = Date.now();

  function _bumpTokens_bl(text) {
    _tokenAccum_bl += (text || '').length / 3.4;
    const now = Date.now();
    if (now - _tokenWindow_bl > 700) {
      const dt = (now - _tokenWindow_bl) / 1000;
      const rate = dt > 0 ? (_tokenAccum_bl / dt).toFixed(1) : '—';
      const el = document.getElementById('tokRate');
      if (el) el.textContent = rate;
      _tokenAccum_bl = 0;
      _tokenWindow_bl = now;
    }
  }

  // ── Helpers ──
  function _isBusyErrorMessage_bl(message) {
    return /(429|rate limit|too many requests|busy|overload|temporarily unavailable|server busy|resource exhausted)/i.test(String(message || ''));
  }

  function _formatRetryDelay_bl(ms) {
    if (!ms || ms < 1000) return `${ms || 0}ms`;
    return `${(ms / 1000).toFixed(ms % 1000 === 0 ? 0 : 1)}s`;
  }

  function _parseUserMessageInput_bl(raw) {
    const text = String(raw || '');
    const match = text.match(/^\[([^\]]+)\]\s+(\S+)\s+\[([^\]]+)\]\s+([\s\S]*)$/);
    if (!match) return { content: text.trim(), time: null };
    return { content: match[4].trim(), time: match[1] };
  }

  function _setConnectionState_bl(text, live) {
    const el = document.getElementById('connState');
    if (!el) return;
    el.innerHTML = live
      ? `<span class="live-dot"></span>${text}`
      : text;
    el.classList.toggle('live', live);
  }

  // ── SSE event dispatcher ──
  function _handle_bl({ type, data = {} }) {
    switch (type) {
      case 'message_received': {
        _currentPath_bl = 'l1';
        // Dispatch custom event so Atlas modules can react
        window.dispatchEvent(new CustomEvent('bl:message_received', { detail: data }));
        const parsed = _parseUserMessageInput_bl(data.input);
        _currentStream_bl()?.newLine('user message received', {
          content: parsed.content,
          time: parsed.time || undefined,
        });
        _currentStream_bl()?.startThinkingSession();
        break;
      }
      case 'tick':
        _currentPath_bl = 'l2';
        _currentStream_bl()?.newLine('heartbeat tick');
        _currentStream_bl()?.startThinkingSession();
        break;
      case 'stream_start':
        _currentStream_bl()?.startThinkingSession();
        break;
      case 'stream_chunk':
        _currentStream_bl()?.clearStatus();
        _bumpTokens_bl(data.text);
        break;
      case 'stream_end':
        _currentStream_bl()?.stopThinking();
        break;
      case 'tool_preparing': {
        const label = data.name ? '准备调用 ' + data.name + '…' : '准备工具调用…';
        _currentStream_bl()?.setStatus(label, 'busy');
        break;
      }
      case 'tool_executing': {
        const label = data.name ? '正在执行 ' + data.name + '…' : '正在执行工具…';
        _currentStream_bl()?.setStatus(label, 'busy');
        break;
      }
      case 'tool_call':
        _currentStream_bl()?.tool(data.name, data.args, data.result, data.ok);
        break;
      case 'response':
        _currentStream_bl()?.end();
        break;
      case 'llm_retry': {
        _currentStream_bl()?.startThinkingSession();
        const nextAttempt = Number(data.nextAttempt || 2);
        const delayText = _formatRetryDelay_bl(Number(data.delayMs || 0));
        _currentStream_bl()?.setStatus(
          'LLM 繁忙，第 ' + nextAttempt + ' 次重试将于 ' + delayText + ' 后开始',
          'busy'
        );
        break;
      }
      case 'message_requeued': {
        _currentStream_bl()?.startThinkingSession();
        const retryCount = Number(data.retryCount || 1);
        _currentStream_bl()?.setStatus('LLM 繁忙，已入队重试 ' + retryCount + '/3', 'busy');
        break;
      }
      case 'message_dropped':
        _currentStream_bl()?.startThinkingSession();
        _currentStream_bl()?.setStatus('LLM 繁忙，重试次数已达上限', 'failed');
        break;
      case 'error':
        if (_isBusyErrorMessage_bl(data.error)) {
          _currentStream_bl()?.startThinkingSession();
          _currentStream_bl()?.setStatus('LLM 繁忙，请稍后重试', 'busy');
        }
        break;
      case 'message':
        if (data.from === 'consciousness') {
          _dispatchEvent_bl('message', data);
        }
        break;
      case 'memories_written':
        window.dispatchEvent(new CustomEvent('bl:memories_written', { detail: data }));
        break;
      case 'agent_name_updated':
        window.dispatchEvent(new CustomEvent('bl:agent_name_updated', { detail: data }));
        break;
      case 'hotspot_mode':
        window.dispatchEvent(new CustomEvent('bl:hotspot_mode', { detail: data }));
        break;
      case 'doc_panel_mode':
        window.dispatchEvent(new CustomEvent('bl:doc_panel_mode', { detail: data }));
        break;
      case 'person_card_mode':
        window.dispatchEvent(new CustomEvent('bl:person_card_mode', { detail: data }));
        break;
      case 'audio_created':
        if (data.autoPlay && data.path) {
          const audioUrl = API_BASE + '/' + data.path;
          new Audio(audioUrl).play().catch(() => {});
        }
        break;
      case 'social_status':
        window.dispatchEvent(new CustomEvent('bl:social_status', { detail: data }));
        break;
      default:
        // Forward unknown events as custom events
        window.dispatchEvent(new CustomEvent('bl:' + type, { detail: data }));
        break;
    }
  }

  // ── SSE connection ──
  function _connectSSE_bl() {
    _setConnectionState_bl('连接中', true);
    const es = new EventSource(API_BASE + '/events');

    es.onopen = () => {
      _connected = true;
      _setConnectionState_bl('已连接', true);
      window.dispatchEvent(new CustomEvent('bl:sse_connected'));
    };

    es.onmessage = (event) => {
      try {
        _handle_bl(JSON.parse(event.data));
      } catch (_) {}
    };

    es.onerror = () => {
      _connected = false;
      _setConnectionState_bl('重连中', false);
      es.close();
      setTimeout(_connectSSE_bl, 3000);
    };
  }

  // ── Public API ──
  return {
    connect: _connectSSE_bl,
    isConnected: () => _connected,
  };
})();
