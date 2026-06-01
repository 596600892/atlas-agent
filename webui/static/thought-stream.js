/* Atlas — Activity Stream & Metrics
   活动流、系统指标、心跳 */

const AtlasStream = (() => {
  const STREAM_MSGS = [
    '📡 扫描市场信号…',
    '🧠 意图路由分析中…',
    '💾 记忆图索引 …',
    '🔄 误差学习循环触发',
    '📊 因子权重更新',
    '⚡ 模式匹配：上升楔形',
    '🔍 跨域关联发现',
    '🌐 知识图谱扩展',
    '🔮 预测引擎活跃',
    '📈 RSI 背离检测',
    '🔗 节点关联完成',
    '🧬 模式学习收敛',
  ];

  let interval = null;

  function add(msg) {
    const container = document.getElementById('streamContainer');
    if (!container) return;

    // 移除 "等待活动信号" 占位
    const first = container.firstElementChild;
    if (first && first.textContent.includes('等待')) first.remove();

    const div = document.createElement('div');
    div.className = 'agent-stream-item';
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    div.innerHTML = `<span class="agent-stream-dot"></span>${msg}<span class="stream-timestamp">${time}</span>`;
    container.prepend(div);
    while (container.children.length > 30) {
      container.lastChild.remove();
    }
  }

  function random() {
    add(STREAM_MSGS[Math.floor(Math.random() * STREAM_MSGS.length)]);
  }

  function updateMetrics(graph) {
    const s = Math.floor((Date.now() - window._atlasStart) / 1000);
    const m = Math.floor(s / 60), h = Math.floor(m / 60);
    const uptime = h > 0 ? `${h}h ${m % 60}m` : m > 0 ? `${m}m ${s % 60}s` : `${s}s`;

    const el = (id) => document.getElementById(id);
    if (el('uptimeDisplay')) el('uptimeDisplay').textContent = uptime;
    if (el('sysUptime')) el('sysUptime').textContent = uptime;
    if (el('nodeCount') && graph) {
      el('nodeCount').textContent = graph.nodes.length;
      el('linkCount').textContent = graph.edges.length;
    }
    if (el('tickChip') && graph) {
      el('tickChip').textContent = `Tick ${graph.tick}`;
    }

    if (el('tokRate')) {
      const tok = (Math.random() * 35 + 15).toFixed(1);
      el('tokRate').textContent = tok;
    }

    // 系统负载模拟（后续可接真实数据）
    const cpu = Math.round(Math.random() * 25 + 10);
    const mem = Math.round(Math.random() * 18 + 35);
    const llm = Math.round(Math.random() * 12 + 5);
    if (el('cpuVal')) el('cpuVal').textContent = cpu + '%';
    if (el('cpuBar')) el('cpuBar').style.width = cpu + '%';
    if (el('memVal')) el('memVal').textContent = mem + '%';
    if (el('memBar')) el('memBar').style.width = mem + '%';
    if (el('llmVal')) el('llmVal').textContent = llm + '%';
    if (el('llmBar')) el('llmBar').style.width = llm + '%';
  }

  function start(graph) {
    window._atlasStart = Date.now();
    updateMetrics(graph);
    interval = setInterval(() => updateMetrics(graph), 2000);
    setInterval(random, 6000);
  }

  function stop() {
    if (interval) clearInterval(interval);
  }

  return { add, random, updateMetrics, start, stop };
})();
