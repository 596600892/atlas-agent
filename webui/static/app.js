/* Atlas — WebUI Entry Point (Module Split)
   初始化所有子系统 */

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

(function init() {
  'use strict';

  // ── 状态 ──
  const state = {
    startTime: Date.now(),
    zoom: parseFloat(localStorage.getItem('atlas-zoom') || '1'),
    provider: localStorage.getItem('atlas-provider') || 'deepseek',
    temperature: parseFloat(localStorage.getItem('atlas-temp') || '0.5'),
    voiceInput: localStorage.getItem('atlas-voice-input') !== 'false',
    tts: localStorage.getItem('atlas-tts') !== 'false',
    tick: 0,
  };

  // ── DOM 缓存 ──
  const el = {
    canvas: $('#graphCanvas'),
    consoleInput: $('#consoleInput'),
    consoleSend: $('#consoleSend'),
    voiceBtn: $('#voiceBtn'),
    settingsBtn: $('#settingsBtn'),
    settingsOverlay: $('#settingsOverlay'),
    settingsClose: $('#settingsClose'),
    toggleRightBtn: $('#toggleRightBtn'),
    secondaryPanel: $('#secondaryPanel'),
    zoomSlider: $('#zoomSlider'),
    zoomValue: $('#zoomValue'),
    providerSelect: $('#providerSelect'),
    customUrlRow: $('#customUrlRow'),
    customUrl: $('#customUrl'),
    tempSlider: $('#tempSlider'),
    tempValue: $('#tempValue'),
    currentModel: $('#currentModel'),
    voiceInputToggle: $('#voiceInputToggle'),
    ttsToggle: $('#ttsToggle'),
    gravitySlider: $('#gravitySlider'),
    gravityVal: $('#gravityVal'),
    repulsionSlider: $('#repulsionSlider'),
    repulsionVal: $('#repulsionVal'),
    sizeSlider: $('#sizeSlider'),
    sizeVal: $('#sizeVal'),
    resetGraphBtn: $('#resetGraphBtn'),
    addNodeBtn: $('#addNodeBtn'),
    streamContainer: $('#streamContainer'),
    nodeCount: $('#nodeCount'),
    linkCount: $('#linkCount'),
    tokRate: $('#tokRate'),
    uptimeDisplay: $('#uptimeDisplay'),
    sysUptime: $('#sysUptime'),
    cpuVal: $('#cpuVal'), cpuBar: $('#cpuBar'),
    memVal: $('#memVal'), memBar: $('#memBar'),
    llmVal: $('#llmVal'), llmBar: $('#llmBar'),
    tickChip: $('#tickChip'),
  };

  // ── 主题 ──
  const savedTheme = AtlasThemes.getStored();
  AtlasThemes.apply(savedTheme);

  // ── 图引擎 ──
  const graph = new ForceGraph(el.canvas);
  graph.loadFromBackend().then(() => {
    AtlasStream.add(`图谱加载: ${graph.nodes.length} 节点 · ${graph.edges.length} 连线`);
  });
  graph.start();

  // ── 聊天 ──
  el.consoleSend.addEventListener('click', () => AtlasChat.send(el.consoleInput.value));
  el.consoleInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      AtlasChat.send(el.consoleInput.value);
    }
  });
  AtlasChat.initVoice(el.voiceBtn);

  // ── 语音面板 ──
  AtlasVoicePanel.init('voicePanel');

  // ── 资料面板 ──
  AtlasProfile.init();

  // ── BaiLongma 增强人物卡片 + 文档面板 ──
  if (typeof BaiLongmaProfile !== 'undefined') {
    BaiLongmaProfile.init();
  }

  // ── 右侧面板标签切换 ──
  document.querySelectorAll('.panel-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.panel-tab-pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const pane = document.getElementById('panel' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1));
      if (pane) pane.classList.add('active');
    });
  });

  // ── 主题选择器 ──
  $$('.theme-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      AtlasThemes.apply(dot.dataset.theme);
      graph.resize();
    });
  });

  // ── 图谱控制 ──
  el.gravitySlider.addEventListener('input', () => {
    graph.gravity = parseFloat(el.gravitySlider.value);
    el.gravityVal.textContent = graph.gravity.toFixed(2);
  });
  el.repulsionSlider.addEventListener('input', () => {
    graph.repulsion = parseFloat(el.repulsionSlider.value);
    el.repulsionVal.textContent = Math.round(graph.repulsion);
  });
  el.sizeSlider.addEventListener('input', () => {
    graph.nodeSize = parseFloat(el.sizeSlider.value);
    el.sizeVal.textContent = graph.nodeSize.toFixed(1) + '×';
  });
  el.resetGraphBtn.addEventListener('click', () => graph.resetLayout());
  el.addNodeBtn.addEventListener('click', () => {
    const labels = ['新记忆', '模式匹配', '异常检测', '数据流', '触发信号'];
    graph.addNode(labels[Math.floor(Math.random() * labels.length)]);
    AtlasStream.add('新增节点: 已连接到图谱');
  });

  // ── 右侧面板 ──
  el.toggleRightBtn.addEventListener('click', () => {
    el.secondaryPanel.classList.toggle('collapsed');
  });

  // ── 设置 ──
  el.settingsBtn.addEventListener('click', () => {
    el.settingsOverlay.hidden = false;
    el.zoomSlider.value = state.zoom;
    el.zoomValue.textContent = Math.round(state.zoom * 100) + '%';
    el.providerSelect.value = state.provider;
    el.customUrlRow.hidden = state.provider !== 'custom';
    el.tempSlider.value = state.temperature;
    el.tempValue.textContent = state.temperature.toFixed(2);
    el.currentModel.textContent = `${state.provider} · ${state.temperature.toFixed(2)}`;
    el.voiceInputToggle.classList.toggle('on', state.voiceInput);
    el.ttsToggle.classList.toggle('on', state.tts);
  });
  el.settingsClose.addEventListener('click', () => { el.settingsOverlay.hidden = true; });
  el.settingsOverlay.addEventListener('click', (e) => {
    if (e.target === el.settingsOverlay) el.settingsOverlay.hidden = true;
  });

  // ── 设置导航 ──
  $$('.settings-nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.settings-nav-btn').forEach(b => b.classList.remove('active'));
      $$('.settings-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const pane = $(`.settings-pane[data-tab="${btn.dataset.tab}"]`);
      if (pane) pane.classList.add('active');
    });
  });

  // ── 设置: 缩放 ──
  el.zoomSlider.addEventListener('input', () => {
    const v = parseFloat(el.zoomSlider.value);
    state.zoom = v;
    localStorage.setItem('atlas-zoom', v);
    el.zoomValue.textContent = Math.round(v * 100) + '%';
    document.documentElement.style.fontSize = (v * 13) + 'px';
  });

  // ── 设置: 提供商 & 温度 ──
  el.providerSelect.addEventListener('change', () => {
    state.provider = el.providerSelect.value;
    localStorage.setItem('atlas-provider', state.provider);
    el.customUrlRow.hidden = state.provider !== 'custom';
    el.currentModel.textContent = `${state.provider} · ${state.temperature.toFixed(2)}`;
  });
  el.tempSlider.addEventListener('input', () => {
    state.temperature = parseFloat(el.tempSlider.value);
    localStorage.setItem('atlas-temp', state.temperature);
    el.tempValue.textContent = state.temperature.toFixed(2);
    el.currentModel.textContent = `${state.provider} · ${state.temperature.toFixed(2)}`;
  });

  // ── 设置: 开关 ──
  el.voiceInputToggle.addEventListener('click', () => {
    state.voiceInput = !state.voiceInput;
    localStorage.setItem('atlas-voice-input', state.voiceInput);
    el.voiceInputToggle.classList.toggle('on', state.voiceInput);
  });
  el.ttsToggle.addEventListener('click', () => {
    state.tts = !state.tts;
    localStorage.setItem('atlas-tts', state.tts);
    el.ttsToggle.classList.toggle('on', state.tts);
  });

  // ── 键盘快捷键 ──
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      el.consoleInput.focus();
    }
    if (e.key === 'Escape') {
      if (!el.settingsOverlay.hidden) el.settingsOverlay.hidden = true;
    }
  });

  // ── 活动流 & 指标 ──
  AtlasStream.start(graph);

  // ── 初始消息 ──
  setTimeout(() => {
    AtlasStream.add('Atlas 记忆图初始化完成');
    AtlasStream.add(`${graph.nodes.length} 节点 · ${graph.edges.length} 连线`);
  }, 500);

  // ── 热点地球 ──
  const hotspotToggle = $('#hotspotToggle');
  if (hotspotToggle) {
    hotspotToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      AtlasHotspot.toggle();
    });
  }

  // ── 窗口 Resize (3D 地球适配) ──
  window.addEventListener('resize', () => {
    AtlasHotspot.resize();
  });

  el.consoleInput.focus();
  console.log(`Atlas WebUI · ${graph.nodes.length}n ${graph.edges.length}e · ${savedTheme} theme`);
})();
