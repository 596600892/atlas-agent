/* Atlas — Force-Directed Memory Graph Engine
   从 /api/memories 加载真实节点数据，支持网络拖拽、引力调节 */

class ForceGraph {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.nodes = [];
    this.edges = [];
    this.width = 0;
    this.height = 0;
    this.animId = null;
    this.mouseX = -9999;
    this.mouseY = -9999;
    this.dragNode = null;
    this.hoverNode = null;
    this.gravity = 0.8;
    this.repulsion = 800;
    this.nodeSize = 1.0;
    this.tick = 0;
    this._loaded = false;

    this.resize();
    this.bindEvents();
  }

  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width * devicePixelRatio;
    this.canvas.height = this.height * devicePixelRatio;
    this.ctx.scale(devicePixelRatio, devicePixelRatio);
  }

  // 从后端加载真实记忆数据
  async loadFromBackend() {
    try {
      const resp = await fetch('/api/memories');
      const data = await resp.json();
      if (data.nodes && data.nodes.length > 0) {
        const cx = this.width / 2, cy = this.height / 2;
        this.nodes = data.nodes.map((n, i) => ({
          id: n.id || i,
          label: n.label || `Node ${i}`,
          content: n.content || '',
          x: cx + (Math.random() - 0.5) * 300,
          y: cy + (Math.random() - 0.5) * 300,
          vx: 0, vy: 0,
          r: 4 + (n.importance || 0.5) * 4,
          pulse: Math.random() * Math.PI * 2,
          group: n.group || 0,
          active: n.active !== false,
          type: n.type || 'node',
        }));
        this.edges = (data.edges || []).map(e => ({
          source: typeof e.source === 'number' ? e.source : this._findNodeIndex(e.source),
          target: typeof e.target === 'number' ? e.target : this._findNodeIndex(e.target),
          weight: e.weight || 0.5,
        })).filter(e => e.source >= 0 && e.target >= 0);
      }
    } catch (e) {
      console.warn('Graph: backend load failed, using seed:', e);
      this.seedNodes();
    }
    this._loaded = true;
  }

  _findNodeIndex(id) {
    return this.nodes.findIndex(n => n.id === id);
  }

  seedNodes() {
    const labels = [
      'Atlas Core', '意图路由', '记忆管理器', '股票分析', '新闻监测',
      '知识图谱', '跨域学习', '主题系统', '误差学习', '权重优化',
      '模式扫描', '文件系统', '语音引擎', 'Git 同步', '活动流',
    ];
    const cx = this.width / 2, cy = this.height / 2;
    this.nodes = labels.map((label, i) => {
      const angle = (i / labels.length) * Math.PI * 2 + Math.random() * 0.2;
      const r = 150 + Math.random() * 80;
      return {
        id: i, label,
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        vx: 0, vy: 0,
        r: 4 + Math.random() * 4,
        pulse: Math.random() * Math.PI * 2,
        group: Math.floor(Math.random() * 4),
        active: Math.random() > 0.5,
        type: 'seed',
      };
    });
    this.edges = [];
    for (let i = 0; i < this.nodes.length; i++) {
      const connections = 1 + Math.floor(Math.random() * 3);
      for (let c = 0; c < connections; c++) {
        let j;
        do { j = Math.floor(Math.random() * this.nodes.length); }
        while (j === i || this.edges.some(e =>
          (e.source === i && e.target === j) || (e.source === j && e.target === i)));
        if (this.edges.length < this.nodes.length * 2) {
          this.edges.push({ source: i, target: j, weight: 0.3 + Math.random() * 0.7 });
        }
      }
    }
  }

  getCSSColor() {
    const s = getComputedStyle(document.documentElement);
    return {
      cool: s.getPropertyValue('--cool').trim(),
      warm: s.getPropertyValue('--warm').trim(),
      glow: s.getPropertyValue('--glow').trim(),
      link: s.getPropertyValue('--link').trim(),
      nodeLow: s.getPropertyValue('--node-low').trim(),
      nodeHigh: s.getPropertyValue('--node-high').trim(),
      bgDeep: s.getPropertyValue('--bg-deep').trim(),
      dim: s.getPropertyValue('--dim').trim(),
      ink2: s.getPropertyValue('--ink2').trim(),
    };
  }

  simulate() {
    this.tick++;
    const cx = this.width / 2, cy = this.height / 2;
    const { cool, link } = this.getCSSColor();
    const dt = 0.3;

    for (const n of this.nodes) {
      if (n === this.dragNode) continue;

      const dxc = cx - n.x, dyc = cy - n.y;
      const dc = Math.sqrt(dxc * dxc + dyc * dyc);
      n.vx += (dxc / (dc || 1)) * this.gravity * 0.01;
      n.vy += (dyc / (dc || 1)) * this.gravity * 0.01;

      for (const o of this.nodes) {
        if (o === n) continue;
        const dx = n.x - o.x, dy = n.y - o.y;
        const d = Math.sqrt(dx * dx + dy * dy) + 0.1;
        if (d < this.repulsion) {
          const force = this.repulsion / (d * d) * 2;
          n.vx += (dx / d) * force * dt;
          n.vy += (dy / d) * force * dt;
        }
      }

      for (const e of this.edges) {
        const a = this.nodes[e.source], b = this.nodes[e.target];
        if (!a || !b) continue;
        if (a === n || b === n) {
          const other = a === n ? b : a;
          const dx = other.x - n.x, dy = other.y - n.y;
          const d = Math.sqrt(dx * dx + dy * dy) + 0.1;
          const ideal = 80;
          const force = (d - ideal) * 0.005;
          n.vx += (dx / d) * force;
          n.vy += (dy / d) * force;
        }
      }

      n.vx *= 0.92;
      n.vy *= 0.92;
      n.x += n.vx * dt;
      n.y += n.vy * dt;
      n.x = Math.max(20, Math.min(this.width - 20, n.x));
      n.y = Math.max(20, Math.min(this.height - 20, n.y));
      n.pulse += 0.03;
    }
  }

  draw() {
    const ctx = this.ctx;
    const { cool, warm, link, nodeLow, nodeHigh, bgDeep, dim } = this.getCSSColor();

    ctx.clearRect(0, 0, this.width, this.height);

    for (const e of this.edges) {
      const a = this.nodes[e.source], b = this.nodes[e.target];
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = link;
      ctx.lineWidth = 0.5 + e.weight * 1.5;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = `rgba(100, 180, 240, ${e.weight * 0.06})`;
      ctx.lineWidth = 2 + e.weight * 3;
      ctx.stroke();
    }

    for (const n of this.nodes) {
      const pulse = Math.sin(n.pulse) * 0.2 + 0.8;
      const radius = n.r * this.nodeSize * pulse;
      const isHover = n === this.hoverNode;
      const color = n.active ? nodeHigh : nodeLow;

      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, radius * 6);
      grad.addColorStop(0, isHover ? `rgba(100, 180, 240, 0.15)` : `rgba(100, 180, 240, 0.05)`);
      grad.addColorStop(1, 'transparent');
      ctx.beginPath();
      ctx.arc(n.x, n.y, radius * 6, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      if (isHover) {
        ctx.strokeStyle = cool;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      if (isHover || radius > 4) {
        ctx.font = `${isHover ? 10 : 9}px "Inter", sans-serif`;
        ctx.fillStyle = isHover ? cool : dim;
        ctx.textAlign = 'center';
        ctx.fillText(n.label, n.x, n.y + radius + 12);
      }
    }

    this.animId = requestAnimationFrame(() => this.draw());
  }

  start() {
    const loop = () => {
      this.simulate();
      this.draw();
      requestAnimationFrame(loop);
    };
    loop();
  }

  bindEvents() {
    window.addEventListener('resize', () => this.resize());

    this.canvas.addEventListener('mousemove', (e) => {
      this.mouseX = e.clientX;
      this.mouseY = e.clientY;
      this.hoverNode = null;
      for (const n of this.nodes) {
        const dx = n.x - e.clientX, dy = n.y - e.clientY;
        if (dx * dx + dy * dy < 200) {
          this.hoverNode = n;
          break;
        }
      }
      this.canvas.style.cursor = this.hoverNode ? 'pointer' : 'default';
      if (this.dragNode) {
        this.dragNode.x = e.clientX;
        this.dragNode.y = e.clientY;
      }
    });

    this.canvas.addEventListener('mousedown', (e) => {
      for (const n of this.nodes) {
        const dx = n.x - e.clientX, dy = n.y - e.clientY;
        if (dx * dx + dy * dy < 200) {
          this.dragNode = n;
          n.vx = 0; n.vy = 0;
          break;
        }
      }
    });

    this.canvas.addEventListener('mouseup', () => { this.dragNode = null; });
    this.canvas.addEventListener('mouseleave', () => { this.hoverNode = null; this.dragNode = null; });
  }

  addNode(label) {
    const cx = this.width / 2 + (Math.random() - 0.5) * 100;
    const cy = this.height / 2 + (Math.random() - 0.5) * 100;
    const id = this.nodes.length;
    this.nodes.push({
      id, label: label || `节点 #${id}`,
      x: cx, y: cy, vx: 0, vy: 0,
      r: 3 + Math.random() * 4,
      pulse: Math.random() * Math.PI * 2,
      group: Math.floor(Math.random() * 4),
      active: true, type: 'manual',
    });
    const nearest = this.nodes.slice(0, -1)
      .map((n, i) => ({ i, d: Math.hypot(n.x - cx, n.y - cy) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, 2);
    for (const n of nearest) {
      this.edges.push({ source: id, target: n.i, weight: 0.5 + Math.random() * 0.5 });
    }
    return id;
  }

  resetLayout() {
    const cx = this.width / 2, cy = this.height / 2;
    this.nodes.forEach((n, i) => {
      const angle = (i / this.nodes.length) * Math.PI * 2;
      const r = 120 + Math.random() * 60;
      n.x = cx + Math.cos(angle) * r;
      n.y = cy + Math.sin(angle) * r;
      n.vx = 0; n.vy = 0;
    });
  }
}
