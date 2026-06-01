/* ───────────────────────────────────────────
   Atlas Agent WebUI — Application Logic
   ─────────────────────────────────────────── */

// ── State ────────────────────────────────────

let currentTab = 'chat';
let isSending = false;

// ── Init ─────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  checkStatus();
  loadAgents();
  loadRoutes();

  // Auto-resize textarea
  const input = document.getElementById('chatInput');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    updateSendButton();
  });

  // Restore theme
  const saved = localStorage.getItem('atlas-theme');
  if (saved === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
});

// ── Tab Switching ────────────────────────────

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

  if (tab === 'chat') {
    document.getElementById('chatInput').focus();
  }
}

// ── Status Check ─────────────────────────────

async function checkStatus() {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');

  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error('Not ready');
    const data = await res.json();
    dot.className = 'status-dot';
    text.textContent = `Ready · ${data.agents} agents · v${data.version}`;
    document.getElementById('versionBadge').textContent = `v${data.version}`;
    document.getElementById('sendBtn').disabled = false;
  } catch (e) {
    dot.className = 'status-dot error';
    text.textContent = 'Server unavailable';
    setTimeout(checkStatus, 2000);
  }
}

// ── Chat ─────────────────────────────────────

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function updateSendButton() {
  const btn = document.getElementById('sendBtn');
  const input = document.getElementById('chatInput');
  btn.disabled = !input.value.trim() || isSending;
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text || isSending) return;

  isSending = true;
  updateSendButton();

  // Add user message
  addMessage('user', '👤', text);

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // Show typing indicator
  const typingId = showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    removeTyping(typingId);

    if (!res.ok) {
      addMessage('atlas', '🧠', 'Sorry, I encountered an error processing your request.');
      isSending = false;
      updateSendButton();
      return;
    }

    const data = await res.json();
    const responseHtml = formatResponse(data);
    addMessage('atlas', '🧠', responseHtml, true);
  } catch (e) {
    removeTyping(typingId);
    addMessage('atlas', '🧠', 'Network error. Please check your connection.');
  }

  isSending = false;
  updateSendButton();
  input.focus();
}

function addMessage(role, avatar, content, isHtml = false) {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  msg.innerHTML = `
    <div class="avatar">${avatar}</div>
    <div class="bubble">
      ${isHtml ? content : `<p>${escapeHtml(content)}</p>`}
      <span class="time">${time}</span>
    </div>
  `;

  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const id = 'typing-' + Date.now();
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = 'message atlas';
  msg.id = id;
  msg.innerHTML = `
    <div class="avatar">🧠</div>
    <div class="bubble">
      <p class="hint">Thinking...</p>
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatResponse(data) {
  let html = `<p>${escapeHtml(data.response)}</p>`;

  const tags = [];
  if (data.intent && data.intent !== 'unknown' && data.intent !== 'error') {
    tags.push(`<span class="intent-tag">🎯 ${escapeHtml(data.intent)} (${(data.confidence * 100).toFixed(0)}%)</span>`);
  }
  if (data.matched_agents && data.matched_agents.length > 0) {
    tags.push(`<span class="intent-tag">🤖 ${data.matched_agents.map(a => a.name).join(', ')}</span>`);
  }
  if (data.memories > 0) {
    tags.push(`<span class="intent-tag">💾 ${data.memories} memories recalled</span>`);
  }

  if (tags.length > 0) {
    html += `<div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">${tags.join('')}</div>`;
  }

  return html;
}

function clearChat() {
  const container = document.getElementById('chatMessages');
  container.innerHTML = `
    <div class="message atlas">
      <div class="avatar">🧠</div>
      <div class="bubble">
        <p>Chat cleared. How can I help you?</p>
        <span class="time">just now</span>
      </div>
    </div>
  `;
}

// ── Agents Tab ───────────────────────────────

async function loadAgents() {
  try {
    const res = await fetch('/api/agents');
    const agents = await res.json();
    const grid = document.getElementById('agentsGrid');
    grid.innerHTML = agents.map(a => `
      <div class="agent-card">
        <h3>${escapeHtml(a.name)}</h3>
        <p class="desc">${escapeHtml(a.description)}</p>
        <div class="caps">
          ${a.capabilities.map(c => `<span class="cap-tag">${escapeHtml(c)}</span>`).join('')}
        </div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('agentsGrid').innerHTML = '<div class="loading">Failed to load agents</div>';
  }
}

// ── Routes Tab ───────────────────────────────

async function loadRoutes() {
  try {
    const res = await fetch('/api/routes');
    const routes = await res.json();
    const container = document.getElementById('routesContainer');

    if (Object.keys(routes).length === 0) {
      container.innerHTML = '<div class="loading">No routes configured</div>';
      return;
    }

    container.innerHTML = Object.entries(routes).map(([cap, agents]) => `
      <div class="route-group">
        <div class="route-header">🎯 ${escapeHtml(cap)}</div>
        <div class="route-body">
          → Routes to: ${agents.map(a => `<strong>${escapeHtml(a)}</strong>`).join(', ')}
        </div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('routesContainer').innerHTML = '<div class="loading">Failed to load routes</div>';
  }
}

// ── Theme ────────────────────────────────────

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  if (isDark) {
    html.removeAttribute('data-theme');
    localStorage.setItem('atlas-theme', 'light');
  } else {
    html.setAttribute('data-theme', 'dark');
    localStorage.setItem('atlas-theme', 'dark');
  }
}

// ── Utils ────────────────────────────────────

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
