/* Atlas — BaiLongma Chat UI (adapted)
   Chat panel with markdown rendering, SSE integration with Hermes API
   All function names use _bl suffix to avoid conflicts with Atlas modules */

const BL_Chat = (() => {
  'use strict';

  const API_BASE = 'http://localhost:8642';

  // ── Simple Markdown Body renderer (replaces missing markdown.js) ──
  // Handles: bold, italic, inline code, code blocks, links, paragraphs
  function _createMarkdownBody_bl(text) {
    const container = document.createElement('div');
    container.className = 'bl-markdown-body';

    if (!text || typeof text !== 'string') {
      container.textContent = String(text || '');
      return container;
    }

    // Split by double newlines for paragraphs
    const blocks = text.split(/\n\n+/);
    let firstBlock = true;

    for (const block of blocks) {
      const trimmed = block.trim();
      if (!trimmed) continue;

      // Code block (```...```)
      const codeMatch = trimmed.match(/^```(\w*)\n([\s\S]*?)\n```$/);
      if (codeMatch) {
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        if (codeMatch[1]) code.className = 'language-' + codeMatch[1];
        code.textContent = codeMatch[2];
        pre.appendChild(code);
        container.appendChild(pre);
        firstBlock = false;
        continue;
      }

      // Single line code block
      const singleCode = trimmed.match(/^```(\w*)\n([\s\S]*?)```$/);
      if (singleCode) {
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = singleCode[2];
        pre.appendChild(code);
        container.appendChild(pre);
        firstBlock = false;
        continue;
      }

      // Process inline markdown within paragraph
      const p = document.createElement('p');
      if (firstBlock) {
        p.style.marginTop = '0';
        firstBlock = false;
      }

      // Parse inline elements: bold, italic, inline code, links
      const segments = trimmed.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))/);
      for (const seg of segments) {
        if (!seg) continue;

        // Bold: **text**
        if (seg.startsWith('**') && seg.endsWith('**')) {
          const strong = document.createElement('strong');
          strong.textContent = seg.slice(2, -2);
          p.appendChild(strong);
          continue;
        }

        // Italic: *text*
        if (seg.startsWith('*') && seg.endsWith('*') && !seg.startsWith('**')) {
          const em = document.createElement('em');
          em.textContent = seg.slice(1, -1);
          p.appendChild(em);
          continue;
        }

        // Inline code: `text`
        if (seg.startsWith('`') && seg.endsWith('`')) {
          const code = document.createElement('code');
          code.textContent = seg.slice(1, -1);
          p.appendChild(code);
          continue;
        }

        // Link: [text](url)
        const linkMatch = seg.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (linkMatch) {
          const a = document.createElement('a');
          a.href = linkMatch[2];
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          a.textContent = linkMatch[1];
          p.appendChild(a);
          continue;
        }

        // Plain text
        p.appendChild(document.createTextNode(seg));
      }

      container.appendChild(p);
    }

    return container;
  }

  // ── Friendly channel label ──
  function _friendlyChannelLabel_bl(channel) {
    if (!channel) return '';
    const c = String(channel).toUpperCase();
    if (c === 'WECHAT_CLAWBOT' || c === 'WECHAT_OFFICIAL' || c === 'WECHAT') return 'WeChat';
    if (c === 'WECOM') return 'WeCom';
    if (c === 'DISCORD') return 'Discord';
    if (c === 'FEISHU') return 'Feishu';
    return '';
  }

  // ── Chat initialization ──
  function _initChat_bl({
    maxHistory = 60,
    activationWarmupKey = 'bailongma_activation_warmup_until',
    getAgentName = () => 'Atlas',
    defaultInputPlaceholder = () => '向 Atlas 发消息…',
    onUserMessage = null,
  } = {}) {
    const chatHistory = document.getElementById('chat-history');
    const chatMessages = document.getElementById('chat-messages');
    const msgInput = document.getElementById('msg-input');
    const chatArea = document.getElementById('chat-area');
    const sendBtn = document.getElementById('send-btn');

    if (!chatHistory || !chatMessages || !msgInput || !chatArea || !sendBtn) {
      console.warn('[BL_Chat] DOM elements not found — chat UI requires #chat-history, #chat-messages, #msg-input, #chat-area, #send-btn');
      return null;
    }

    let inputLocked = false;
    let closeTimer = null;
    let hasPendingJarvisMessage = false;
    let pendingMessageDismissed = false;
    let audioCtx = null;
    let audioUnlocked = false;
    let warmupTimer = null;

    function setComposerLocked_bl(locked, reason) {
      inputLocked = locked;
      msgInput.disabled = locked;
      sendBtn.disabled = locked;
      msgInput.placeholder = locked ? (reason || '系统准备中…') : defaultInputPlaceholder();
    }

    function releaseWarmupLock_bl() {
      if (warmupTimer) {
        clearTimeout(warmupTimer);
        warmupTimer = null;
      }
      try {
        sessionStorage.removeItem(activationWarmupKey);
      } catch {}
      setComposerLocked_bl(false);
    }

    function applyActivationWarmupLock_bl() {
      let until = 0;
      try {
        until = Number(sessionStorage.getItem(activationWarmupKey) || 0);
      } catch {}

      const remaining = until - Date.now();
      if (remaining <= 0) {
        releaseWarmupLock_bl();
        return;
      }

      const seconds = Math.max(1, Math.ceil(remaining / 1000));
      setComposerLocked_bl(true, '刚激活 — 模型预热中… ~' + seconds + 's');
      if (warmupTimer) clearTimeout(warmupTimer);
      warmupTimer = setTimeout(releaseWarmupLock_bl, remaining);
    }

    function isHoveringChat_bl() {
      return chatArea.matches(':hover') || chatHistory.matches(':hover') || chatMessages.matches(':hover');
    }

    function ensureAudioContext_bl() {
      if (!audioCtx) {
        if (!audioUnlocked) return null;
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return null;
        try {
          audioCtx = new AudioCtx();
        } catch {
          return null;
        }
      }
      return audioCtx;
    }

    function unlockAudioOnFirstGesture_bl() {
      const unlock = () => {
        if (audioUnlocked) return;
        audioUnlocked = true;
        const ctx = ensureAudioContext_bl();
        if (ctx && ctx.state === 'suspended') {
          ctx.resume().catch(() => {});
        }
        window.removeEventListener('pointerdown', unlock, true);
        window.removeEventListener('keydown', unlock, true);
        window.removeEventListener('touchstart', unlock, true);
      };
      window.addEventListener('pointerdown', unlock, true);
      window.addEventListener('keydown', unlock, true);
      window.addEventListener('touchstart', unlock, true);
    }

    async function playJarvisAlert_bl() {
      const ctx = ensureAudioContext_bl();
      if (!ctx) return;
      try {
        if (ctx.state === 'suspended') await ctx.resume();
      } catch {
        return;
      }
      if (ctx.state !== 'running') return;
      const now = ctx.currentTime;
      const master = ctx.createGain();
      master.gain.setValueAtTime(0.0001, now);
      master.gain.exponentialRampToValueAtTime(0.3, now + 0.02);
      master.gain.exponentialRampToValueAtTime(0.18, now + 0.28);
      master.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
      master.connect(ctx.destination);

      const oscA = ctx.createOscillator();
      oscA.type = 'sine';
      oscA.frequency.setValueAtTime(740, now);
      oscA.frequency.exponentialRampToValueAtTime(880, now + 0.18);
      oscA.connect(master);

      const oscB = ctx.createOscillator();
      oscB.type = 'triangle';
      oscB.frequency.setValueAtTime(1110, now + 0.12);
      oscB.frequency.exponentialRampToValueAtTime(1320, now + 0.34);
      oscB.connect(master);

      oscA.start(now);
      oscA.stop(now + 0.32);
      oscB.start(now + 0.12);
      oscB.stop(now + 0.5);

      oscA.addEventListener('ended', () => oscA.disconnect(), { once: true });
      oscB.addEventListener('ended', () => oscB.disconnect(), { once: true });
      setTimeout(() => master.disconnect(), 700);
    }

    function isTyping_bl() {
      return document.activeElement === msgInput || msgInput.value.trim().length > 0;
    }

    async function fetchChatHistory_bl() {
      try {
        const res = await fetch(API_BASE + '/conversations?limit=' + maxHistory);
        if (!res.ok) return [];
        const rows = await res.json();
        if (!Array.isArray(rows)) return [];
        return rows
          .filter((r) => r && (r.role === 'user' || r.role === 'jarvis') && typeof r.content === 'string')
          .map((r) => {
            const channel = (r.channel || '').toUpperCase();
            const isExternal =
              r.role === 'user' &&
              ((channel && channel !== 'TUI' && channel !== 'API' && channel !== 'SYSTEM' && channel !== 'REMINDER' && channel !== 'APP_SIGNAL' && channel !== 'VOICE' && channel !== '语音识别') ||
                /^(wechat|discord|feishu|wecom):/i.test(r.from_id || ''));
            if (isExternal) {
              const label = _friendlyChannelLabel_bl(r.channel) || r.from_id;
              return { role: 'external', text: r.content, label };
            }
            return { role: r.role, text: r.content };
          });
      } catch {
        return [];
      }
    }

    function openChat_bl(autoClose) {
      chatHistory.classList.add('open');
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      if (autoClose && (!hasPendingJarvisMessage || pendingMessageDismissed) && !isTyping_bl()) {
        scheduleClose_bl(4500);
      }
    }

    function closeChat_bl() {
      if ((hasPendingJarvisMessage && !pendingMessageDismissed) || isTyping_bl() || isHoveringChat_bl()) return;
      chatHistory.classList.remove('open');
    }

    function scheduleClose_bl(ms) {
      if ((hasPendingJarvisMessage && !pendingMessageDismissed) || isTyping_bl() || isHoveringChat_bl()) return;
      if (closeTimer) clearTimeout(closeTimer);
      closeTimer = setTimeout(closeChat_bl, ms || 100);
    }

    function addMsg_bl(role, text, options) {
      options = options || {};
      const { alert = role === 'jarvis', pending = true, label } = options;
      const defaultLabel = role === 'user' ? 'You' : role === 'jarvis' ? getAgentName() : 'Peer';
      const labelText = label || defaultLabel;
      const div = document.createElement('div');
      div.className = 'msg msg-' + role;
      const labelSpan = document.createElement('span');
      labelSpan.className = 'msg-label';
      labelSpan.textContent = labelText;
      div.appendChild(labelSpan);
      div.appendChild(_createMarkdownBody_bl(text));
      chatMessages.appendChild(div);

      while (chatMessages.children.length > maxHistory) {
        chatMessages.removeChild(chatMessages.firstChild);
      }

      if (role === 'jarvis') {
        hasPendingJarvisMessage = pending;
        pendingMessageDismissed = !pending;
        if (alert) playJarvisAlert_bl();
        if (pending) openChat_bl();
      } else if (role === 'user') {
        hasPendingJarvisMessage = false;
        pendingMessageDismissed = false;
      }

      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function restoreChatHistory_bl() {
      const history = await fetchChatHistory_bl();
      history.forEach((i) => addMsg_bl(i.role, i.text, { persist: false, alert: false, pending: false, label: i.label }));
      if (history.length) {
        pendingMessageDismissed = true;
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
    }

    async function send_bl(channel, label) {
      if (inputLocked) return;
      const text = msgInput.value.trim();
      if (!text) return;
      msgInput.value = '';
      const override = onUserMessage ? onUserMessage(text) : null;
      addMsg_bl('user', text, { label: label || undefined });
      openChat_bl();
      scheduleClose_bl(1000);
      if (override === false) return;

      try {
        const backendText = typeof override === 'string' ? override : text;
        const payload = { content: backendText, from_id: 'ID:000001' };
        if (channel) payload.channel = channel;
        const resp = await fetch(API_BASE + '/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          let message = 'HTTP ' + resp.status;
          try {
            const body = await resp.json();
            message = body.error || body.message || message;
          } catch {}
          throw new Error(message);
        }
      } catch (error) {
        console.warn('[BL_Chat send]', error.message);
        addMsg_bl('jarvis', '发送失败 — 请检查本地服务是否运行。');
        openChat_bl(true);
      }
    }

    function deleteLastUserMsg_bl() {
      const msgs = chatMessages.querySelectorAll('.msg-user');
      if (!msgs.length) return;
      const last = msgs[msgs.length - 1];
      last.style.transition = 'opacity 0.3s ease';
      last.style.opacity = '0';
      setTimeout(() => last.remove(), 300);
    }

    function updateLastJarvisMsg_bl(newText) {
      const msgs = chatMessages.querySelectorAll('.msg-jarvis');
      if (!msgs.length) return;
      const last = msgs[msgs.length - 1];
      const children = Array.from(last.children);
      for (let i = 1; i < children.length; i++) children[i].remove();
      last.appendChild(_createMarkdownBody_bl(newText));
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // ── Event bindings ──
    chatArea.addEventListener('mouseenter', () => {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      openChat_bl();
    });
    chatArea.addEventListener('mouseleave', () => scheduleClose_bl());
    msgInput.addEventListener('focus', () => openChat_bl());
    msgInput.addEventListener('blur', () => {
      if (!isTyping_bl()) scheduleClose_bl();
    });
    msgInput.addEventListener('input', () => {
      if (isTyping_bl()) openChat_bl();
      else if (!hasPendingJarvisMessage || pendingMessageDismissed) scheduleClose_bl();
    });
    msgInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        send_bl();
      }
    });
    sendBtn.addEventListener('click', () => send_bl());

    document.addEventListener('pointerdown', (event) => {
      if (chatArea.contains(event.target)) return;
      if (hasPendingJarvisMessage && !isTyping_bl()) {
        pendingMessageDismissed = true;
        closeChat_bl();
        return;
      }
      if (!isTyping_bl()) {
        if (closeTimer) {
          clearTimeout(closeTimer);
          closeTimer = null;
        }
        chatHistory.classList.remove('open');
      }
    });

    return {
      addMsg: addMsg_bl,
      deleteLastUserMsg: deleteLastUserMsg_bl,
      updateLastJarvisMsg: updateLastJarvisMsg_bl,
      applyActivationWarmupLock: applyActivationWarmupLock_bl,
      isComposerLocked: () => inputLocked,
      isTyping: isTyping_bl,
      openChat: openChat_bl,
      restoreChatHistory: restoreChatHistory_bl,
      send: send_bl,
      unlockAudioOnFirstGesture: unlockAudioOnFirstGesture_bl,
    };
  }

  // ── Public API ──
  return {
    initChat: _initChat_bl,
    friendlyChannelLabel: _friendlyChannelLabel_bl,
    createMarkdownBody: _createMarkdownBody_bl,
    // Internal hooks (used by BL_SSE)
    _addMsg_bl: null,  // Set after init
    _openChat_bl: null, // Set after init
  };
})();
