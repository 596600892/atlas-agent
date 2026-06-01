/* Atlas — Profile Panel (人物卡片 + 文档面板)
   聊天中检测人名 → 右侧面板显示人物画像
   支持维基百科数据拉取、标签、相关文档
   ──────────────────────────────────────────────────── */

const AtlasProfile = (() => {
  'use strict';

  // 已知人物库 (初始 seed)
  const KNOWN = {
    'atlas': { name: 'Atlas', role: '全能智能体', desc: '自适应学习引擎 · 跨域推理 · 记忆图' },
    'hermes': { name: 'Hermes', role: 'AI 助手', desc: 'Nous Research 开发的多模态对话 AI' },
    'deepseek': { name: 'DeepSeek', role: 'LLM 提供商', desc: '深度求索，高性能开源大语言模型' },
    'bailongma': { name: 'BaiLongma', role: '参考项目', desc: '开源 AI 全能助手 WebUI 参考实现' },
  };

  let currentPerson = null;
  let wikiCache = {};

  // ── 从文本中检测人名 ──
  function detectPeople(text) {
    if (!text) return [];
    // 检测 @提及 或 已知人名
    const mentions = text.match(/@(\w+)/g) || [];
    const found = mentions.map(m => m.slice(1).toLowerCase());

    // 检测已知词
    const lower = text.toLowerCase();
    for (const key of Object.keys(KNOWN)) {
      if (lower.includes(key) && !found.includes(key)) {
        found.push(key);
      }
    }

    return [...new Set(found)];
  }

  // ── 显示人物卡片 ──
  function show(personId) {
    const id = personId.toLowerCase();
    currentPerson = id;
    const data = KNOWN[id];

    const container = document.getElementById('profileContainer');
    if (!container) return;

    if (!data) {
      // 未知人物：使用临时数据
      showTemporary(id);
      return;
    }

    const html = `
      <div class="profile-card">
        <div class="profile-avatar">${data.name.charAt(0).toUpperCase()}</div>
        <div class="profile-info">
          <div class="profile-name">${data.name}</div>
          <div class="profile-role">${data.role || '未知角色'}</div>
          <div class="profile-desc">${data.desc || ''}</div>
        </div>
        <div class="profile-tags">
          <span class="profile-tag">${id}</span>
          ${data.role ? `<span class="profile-tag">${data.role}</span>` : ''}
        </div>
        <div class="profile-actions">
          <button class="profile-btn wiki-btn" data-person="${id}">📖 维基百科</button>
          <button class="profile-btn close-profile">✕ 关闭</button>
        </div>
        <div class="profile-wiki" id="profileWiki"></div>
      </div>
    `;

    container.innerHTML = html;

    // 绑定按钮
    container.querySelector('.wiki-btn')?.addEventListener('click', (e) => {
      fetchWiki(e.target.dataset.person);
    });
    container.querySelector('.close-profile')?.addEventListener('click', () => {
      container.innerHTML = '<div class="profile-empty">点击人物名查看资料</div>';
    });
  }

  // ── 未知人物临时卡片 ──
  function showTemporary(name) {
    const container = document.getElementById('profileContainer');
    if (!container) return;
    container.innerHTML = `
      <div class="profile-card temp">
        <div class="profile-avatar">${name.charAt(0).toUpperCase()}</div>
        <div class="profile-info">
          <div class="profile-name">${name}</div>
          <div class="profile-role">未知实体</div>
          <div class="profile-desc">尚未录入知识库。尝试通过聊天了解更多信息。</div>
        </div>
        <div class="profile-actions">
          <button class="profile-btn wiki-btn" data-person="${name}">📖 维基百科</button>
          <button class="profile-btn close-profile">✕ 关闭</button>
        </div>
        <div class="profile-wiki" id="profileWiki"></div>
      </div>
    `;
    container.querySelector('.wiki-btn')?.addEventListener('click', (e) => {
      fetchWiki(e.target.dataset.person);
    });
    container.querySelector('.close-profile')?.addEventListener('click', () => {
      container.innerHTML = '<div class="profile-empty">点击人物名查看资料</div>';
    });
  }

  // ── 维基百科查询 ──
  async function fetchWiki(name) {
    const wikiEl = document.getElementById('profileWiki');
    if (!wikiEl) return;

    if (wikiCache[name]) {
      wikiEl.innerHTML = wikiCache[name];
      wikiEl.classList.add('open');
      return;
    }

    wikiEl.innerHTML = '<div class="wiki-loading">⏳ 查询维基百科…</div>';
    wikiEl.classList.add('open');

    try {
      const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(name)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const html = `
        <div class="wiki-result">
          ${data.thumbnail ? `<img class="wiki-thumb" src="${data.thumbnail.source}" alt="${name}">` : ''}
          <div class="wiki-title">${data.title}</div>
          <div class="wiki-extract">${data.extract || '无摘要'}</div>
          <a class="wiki-link" href="${data.content_urls?.desktop?.page || '#'}" target="_blank" rel="noopener">↗ 查看完整页面</a>
        </div>
      `;
      wikiCache[name] = html;
      wikiEl.innerHTML = html;
    } catch (err) {
      wikiEl.innerHTML = `<div class="wiki-error">⚠ ${err.message}</div>`;
    }
  }

  // ── 注册新人物 ──
  function register(name, role, desc) {
    const id = name.toLowerCase();
    KNOWN[id] = { name, role, desc };
    if (currentPerson === id) show(id);
  }

  // ── 初始化 ──
  function init() {
    const container = document.getElementById('profileContainer');
    if (container) {
      container.innerHTML = '<div class="profile-empty">点击人物名查看资料</div>';
    }
  }

  return { detectPeople, show, register, init };
})();
