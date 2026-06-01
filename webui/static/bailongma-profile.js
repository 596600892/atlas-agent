/* Atlas — 增强人物卡片 + 资料面板 (移植自 BaiLongma)
   提供更丰富的人物画像：头像、代表作、标签、维基百科、来源
   以及文档面板：多章节导航、Tab 切换、内联配置
   ──────────────────────────────────────────────────────────────── */

const BaiLongmaProfile = (() => {
  'use strict';

  // ── 配置 ────────────────────────────────────────────────────
  const API_BASE = 'http://localhost:8642';
  const REVEAL_DELAY_MS = 800;
  const LEAVE_MS = 220;
  const ENTER_MS = 280;

  let imageLookupToken = 0;
  let personCardActive_bl = false;
  let currentCard_bl = null;
  let revealTimer_bl = null;
  let animationTimer_bl = null;

  // 文档面板状态
  let docActive_bl = false;
  let currentTopicId_bl = null;
  let currentDoc_bl = null;
  let ttlTimer_bl = null;

  // ── 内部工具 ────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  function normalizeList_bl(value) {
    if (Array.isArray(value)) return value.map(v => String(v || '').trim()).filter(Boolean);
    if (typeof value === 'string') return value.split(/[,，、;；\\n]/).map(v => v.trim()).filter(Boolean);
    return [];
  }

  function uniqueList_bl(items = []) {
    return [...new Set(items.map(v => String(v || '').trim()).filter(Boolean))];
  }

  function cleanLine_bl(value = '') {
    return String(value || '')
      .replace(/^[\s>*\-•·]+/, '')
      .replace(/\*\*/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function formatUpdatedAt_bl(value) {
    if (!value) return '--';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '--';
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function initials_bl(name = '') {
    const compact = String(name || '').trim();
    if (!compact) return '?';
    const chars = [...compact.replace(/\s+/g, '')];
    return chars.slice(0, Math.min(2, chars.length)).join('');
  }

  function setText_bl(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
  }

  // ── 维基百科图像查找 ──────────────────────────────────────────
  async function findPersonImage_bl(name = '') {
    const query = String(name || '').trim();
    if (!query || query === '人物卡片' || query === '未知人物') return '';
    const endpoints = [
      `https://zh.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`,
      `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`,
    ];
    for (const url of endpoints) {
      try {
        const res = await fetch(url, { headers: { Accept: 'application/json' } });
        if (!res.ok) continue;
        const data = await res.json();
        const image = data?.thumbnail?.source || data?.originalimage?.source || '';
        if (image) return image;
      } catch { /* ignore */ }
    }
    return '';
  }

  // ── 渲染人物卡片 ────────────────────────────────────────────
  function renderPersonCard_bl(card = {}) {
    currentCard_bl = card;
    const container = $('profileContainer');
    if (!container) return;

    const name = String(card.name || '未知人物').trim();
    const title = card.title || '人物卡片';
    const summary = card.summary || '暂无简介。';
    const source = `来源：${card.source || '人物卡片'}`;
    const updated = formatUpdatedAt_bl(card.updatedAt);
    const explicitImage = String(card.image || card.avatar || '').trim();

    const knownFor = normalizeList_bl(card.knownFor);
    const tags = normalizeList_bl(card.tags);

    // 构建 HTML
    const html = `
      <div class="bl-pc-card">
        <div class="bl-pc-hero ${explicitImage ? 'bl-pc-hero-has-image' : ''}" id="bl-pc-hero">
          <img id="bl-pc-hero-img" src="${explicitImage}" alt="${explicitImage ? name : ''}" ${explicitImage ? '' : 'hidden'}>
          <span class="bl-pc-hero-fallback" id="bl-pc-hero-fallback">${initials_bl(name)}</span>
        </div>
        <div class="bl-pc-header">
          <div class="bl-pc-head-copy">
            <div class="bl-pc-kicker">${title}</div>
            <div class="bl-pc-name" id="bl-pc-name">${name}</div>
            <div class="bl-pc-title" id="bl-pc-title">${title}</div>
          </div>
        </div>
        <div class="bl-pc-summary" id="bl-pc-summary">${summary}</div>
        <div class="bl-pc-section">
          <div class="bl-pc-section-title">代表作品 / 识别点</div>
          <ul class="bl-pc-known-list" id="bl-pc-known-list">
            ${knownFor.length === 0
              ? '<li>暂无代表作品或识别点</li>'
              : knownFor.slice(0, 6).map(item => `<li>${item}</li>`).join('')
            }
          </ul>
        </div>
        <div class="bl-pc-tags" id="bl-pc-tags">
          ${tags.slice(0, 8).map(t => `<span class="bl-pc-tag">${t}</span>`).join('')}
        </div>
        <div class="bl-pc-footer">
          <span class="bl-pc-source">${source}</span>
          <span class="bl-pc-updated">${updated}</span>
        </div>
        <div class="bl-pc-actions">
          <button class="bl-pc-wiki-btn" data-person="${name}">📖 维基百科</button>
          <button class="bl-pc-close-btn">✕ 关闭</button>
        </div>
        <div class="bl-pc-wiki" id="bl-pc-wiki"></div>
      </div>
    `;

    container.innerHTML = html;

    // 绑定事件
    container.querySelector('.bl-pc-wiki-btn')?.addEventListener('click', (e) => {
      fetchWiki_bl(e.target.dataset.person);
    });
    container.querySelector('.bl-pc-close-btn')?.addEventListener('click', () => {
      container.innerHTML = '<div class="profile-empty">点击人物名 @提及 查看资料</div>';
    });

    // 异步查找头像
    scheduleHeroImageLookup_bl(card);
  }

  function scheduleHeroImageLookup_bl(card = {}) {
    const name = String(card.name || '').trim();
    const explicitImage = String(card.image || card.avatar || '').trim();
    const token = ++imageLookupToken;
    if (explicitImage) return;
    findPersonImage_bl(name).then((image) => {
      if (token !== imageLookupToken || !image) return;
      if (currentCard_bl?.name !== name) return;
      const heroImg = $('bl-pc-hero-img');
      const hero = $('bl-pc-hero');
      if (heroImg) {
        heroImg.src = image;
        heroImg.alt = name;
        heroImg.hidden = false;
      }
      if (hero) hero.classList.add('bl-pc-hero-has-image');
    });
  }

  // ── 维基百科查询 ────────────────────────────────────────────
  let wikiCache_bl = {};

  async function fetchWiki_bl(name) {
    const wikiEl = $('bl-pc-wiki');
    if (!wikiEl) return;

    if (wikiCache_bl[name]) {
      wikiEl.innerHTML = wikiCache_bl[name];
      wikiEl.classList.add('open');
      return;
    }

    wikiEl.innerHTML = '<div class="bl-wiki-loading">⏳ 查询维基百科…</div>';
    wikiEl.classList.add('open');

    try {
      const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(name)}`;
      const res = await fetch(url);
      if (!res.ok) {
        // 尝试中文维基
        const zhUrl = `https://zh.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(name)}`;
        const zhRes = await fetch(zhUrl);
        if (!zhRes.ok) throw new Error(`HTTP ${zhRes.status}`);
        const data = await zhRes.json();
        renderWikiResult_bl(wikiEl, data, name);
        return;
      }
      const data = await res.json();
      renderWikiResult_bl(wikiEl, data, name);
    } catch (err) {
      wikiEl.innerHTML = `<div class="bl-wiki-error">⚠ ${err.message}</div>`;
    }
  }

  function renderWikiResult_bl(el, data, name) {
    const html = `
      <div class="bl-wiki-result">
        ${data.thumbnail ? `<img class="bl-wiki-thumb" src="${data.thumbnail.source}" alt="${name}">` : ''}
        <div class="bl-wiki-title">${data.title}</div>
        <div class="bl-wiki-extract">${data.extract || '无摘要'}</div>
        <a class="bl-wiki-link" href="${data.content_urls?.desktop?.page || '#'}" target="_blank" rel="noopener">↗ 查看完整页面</a>
      </div>
    `;
    wikiCache_bl[name] = html;
    el.innerHTML = html;
  }

  // ── API 调用 ────────────────────────────────────────────────
  async function fetchPersonCard_bl(name) {
    try {
      const res = await fetch(`${API_BASE}/person-card?name=${encodeURIComponent(name)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.card || null;
    } catch (err) {
      console.warn('[BaiLongmaProfile] 人物卡片加载失败:', err.message);
      return null;
    }
  }

  async function fetchDoc_bl(topicId) {
    try {
      const res = await fetch(`${API_BASE}/docs/${topicId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.doc || null;
    } catch (err) {
      console.warn('[BaiLongmaProfile] 获取文档失败:', err.message);
      return null;
    }
  }

  // ── 公开 API: 显示人物卡片 ──────────────────────────────────
  function show_bl(name, { source = 'brain-ui' } = {}) {
    const query = String(name || '').trim();
    if (!query) return;

    // 切换到资料标签
    const profileTab = document.querySelector('.panel-tab[data-tab="profile"]');
    if (profileTab) profileTab.click();

    const container = $('profileContainer');
    if (!container) return;

    container.innerHTML = '<div class="bl-loading">⏳ 加载人物资料…</div>';

    fetchPersonCard_bl(query).then(card => {
      if (card) {
        renderPersonCard_bl(card);
      } else {
        // 降级：使用本地信息
        renderPersonCard_bl({
          name: query,
          title: '人物卡片',
          summary: '暂时没有资料。可以让 AI 补充这个人的身份和代表作品。',
          knownFor: [],
          tags: ['待补充'],
          source: 'fallback',
          updatedAt: new Date().toISOString(),
        });
      }
    }).catch(() => {
      renderPersonCard_bl({
        name: query,
        title: '人物卡片',
        summary: '加载失败。请检查 Hermes API 连接。',
        knownFor: [],
        tags: ['待补充'],
        source: 'error',
        updatedAt: new Date().toISOString(),
      });
    });
  }

  // ── 从文本检测人名 ──────────────────────────────────────────
  function detectPeople_bl(text) {
    if (!text) return [];
    const mentions = text.match(/@(\w+)/g) || [];
    return [...new Set(mentions.map(m => m.slice(1).toLowerCase()))];
  }

  // ── 文档面板 ──────────────────────────────────────────────────
  function renderProviders_bl(providers) {
    const el = $('dp-providers');
    if (!el) return;
    if (!providers || providers.length === 0) {
      el.style.display = 'none';
      return;
    }
    el.style.display = 'flex';
    el.innerHTML = providers.map(p => `
      <a class="dp-provider-chip${p.free ? ' dp-provider-free' : ''}" href="${p.url}" target="_blank" rel="noopener" title="${p.note || ''}">
        <span class="dp-chip-name">${p.name}</span>
        ${p.free ? '<span class="dp-chip-badge">免费</span>' : ''}
        <span class="dp-chip-arrow">↗</span>
      </a>
    `).join('');
  }

  function renderNav_bl(sections, activeIdx = 0) {
    const nav = $('dp-nav');
    if (!nav) return;
    nav.innerHTML = sections.map((s, i) => `
      <button class="dp-nav-item${i === activeIdx ? ' dp-nav-active' : ''}" data-idx="${i}" type="button">
        <span class="dp-nav-num">${String(i + 1).padStart(2, '0')}</span>
        <span class="dp-nav-label">${s.title}</span>
      </button>
    `).join('');

    nav.querySelectorAll('.dp-nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        renderSection_bl(parseInt(btn.dataset.idx, 10));
      });
    });
  }

  function renderSection_bl(idx) {
    if (!currentDoc_bl || !currentDoc_bl.sections[idx]) return;
    const section = currentDoc_bl.sections[idx];
    const content = $('dp-content');
    if (content) {
      content.innerHTML = `
        <div class="dp-section-title">${section.title}</div>
        <div class="dp-section-body">${formatContent_bl(section.content)}</div>
      `;
    }
    const nav = $('dp-nav');
    if (nav) {
      nav.querySelectorAll('.dp-nav-item').forEach((btn, i) => {
        btn.classList.toggle('dp-nav-active', i === idx);
      });
    }
  }

  function formatContent_bl(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/(https?:\/\/[^\s\)]+)/g, '<a href="$1" target="_blank" rel="noopener" class="dp-link">$1</a>')
      .replace(/^■ (.+)$/gm, '<div class="dp-bullet">■ $1</div>')
      .replace(/^→ (.+)$/gm, '<div class="dp-arrow-item">→ $1</div>')
      .replace(/^(\d+)\. (.+)$/gm, '<div class="dp-list-item"><span class="dp-list-num">$1.</span> $2</div>')
      .replace(/^([①②③④⑤⑥⑦⑧⑨]) (.+)$/gm, '<div class="dp-list-item"><span class="dp-list-num">$1</span> $2</div>')
      .replace(/\n/g, '<br>');
  }

  function renderDoc_bl(doc) {
    currentDoc_bl = doc;
    const title = $('dp-title');
    const subtitle = $('dp-subtitle');
    const icon = $('dp-icon');
    const summary = $('dp-summary');
    if (title) title.textContent = doc.title;
    if (subtitle) subtitle.textContent = doc.subtitle || '';
    if (icon) icon.textContent = doc.icon || '📄';
    if (summary) summary.textContent = doc.summary || '';

    // 更新 Tab 高亮
    const tabs = $('dp-tabs');
    if (tabs) {
      tabs.querySelectorAll('.dp-tab').forEach(btn => {
        btn.classList.toggle('dp-tab-active', btn.dataset.topic === doc.id);
      });
    }
    renderNav_bl(doc.sections, 0);
    renderSection_bl(0);
    renderProviders_bl(doc.providers);
  }

  async function loadTopic_bl(topicId) {
    if (!topicId) return;
    currentTopicId_bl = topicId;
    const content = $('dp-content');
    if (content) content.innerHTML = '<div class="dp-loading">加载中...</div>';
    const doc = await fetchDoc_bl(topicId);
    if (doc) renderDoc_bl(doc);
  }

  function startTTLDisplay_bl() {
    let remaining = 30 * 60;
    const el = $('dp-footer-ttl');
    if (ttlTimer_bl) clearInterval(ttlTimer_bl);
    ttlTimer_bl = setInterval(() => {
      remaining = Math.max(0, remaining - 1);
      const min = Math.ceil(remaining / 60);
      if (el) el.textContent = remaining > 0 ? `上下文有效期 ${min} 分钟` : '上下文已过期';
      if (remaining === 0) clearInterval(ttlTimer_bl);
    }, 1000);
  }

  function stopTTLDisplay_bl() {
    if (ttlTimer_bl) clearInterval(ttlTimer_bl);
    ttlTimer_bl = null;
  }

  function setDocPanelVisible_bl(visible) {
    docActive_bl = visible;
    const panel = $('doc-panel');
    if (panel) panel.classList.toggle('dp-visible', visible);
  }

  function showDoc_bl(topicId = 'voice_config') {
    setDocPanelVisible_bl(true);
    startTTLDisplay_bl();
    if (topicId !== currentTopicId_bl || !currentDoc_bl) {
      loadTopic_bl(topicId);
    }
  }

  function hideDoc_bl() {
    setDocPanelVisible_bl(false);
    stopTTLDisplay_bl();
  }

  function toggleDoc_bl(topicId) {
    if (docActive_bl) {
      hideDoc_bl();
    } else {
      showDoc_bl(topicId);
    }
  }

  // ── 初始化 ──────────────────────────────────────────────────
  function init_bl() {
    const container = $('profileContainer');
    if (container) {
      container.innerHTML = '<div class="profile-empty">点击人物名 @提及 查看资料</div>';
    }

    // 绑定文档面板 Tab 切换
    const tabs = $('dp-tabs');
    if (tabs) {
      tabs.querySelectorAll('.dp-tab').forEach(btn => {
        btn.addEventListener('click', () => {
          const topic = btn.dataset.topic;
          if (topic) {
            showDoc_bl(topic);
          }
        });
      });
    }

    // 绑定文档面板关闭按钮
    const closeBtn = $('dp-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', hideDoc_bl);
  }

  // ── 公开接口 ──
  return {
    show: show_bl,
    detectPeople: detectPeople_bl,
    showDoc: showDoc_bl,
    hideDoc: hideDoc_bl,
    toggleDoc: toggleDoc_bl,
    init: init_bl,
  };
})();
