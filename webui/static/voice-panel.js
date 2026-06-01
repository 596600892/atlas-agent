/* Atlas — Voice Panel (声波点云球)
   Canvas 2D Fibonacci 球面采样 + 8态颜色 + 打断检测
   基于 BaiLongma 设计思想，零后端，纯 Web Speech API
   ──────────────────────────────────────────────────────────
   状态: idle | listening | thinking | speaking | error | interrupted
*/

const AtlasVoicePanel = (() => {
  'use strict';

  // ── 配置 ──
  const CONFIG = {
    count: 1200,       // 球面点数 (Fibonacci)
    radius: 100,       // 投影半径 px
    rotation: { x: 0.01, y: 0.008 },
    duckThreshold: 0.6,   // 打断阈值 (0-1)
    sustainMs: 400,       // 持续高振幅才打断
    recoveryMs: 1500,     // 误触发自动恢复
    preBufferMs: 1200,    // 预缓冲时长
    stateColors: {
      idle:        { r: 100, g: 120, b: 180, a: 0.5 },
      listening:   { r: 60,  g: 200, b: 120, a: 0.9 },
      thinking:    { r: 160, g: 120, b: 255, a: 0.8 },
      speaking:    { r: 80,  g: 180, b: 255, a: 0.9 },
      error:       { r: 255, g: 70,  b: 70,  a: 0.8 },
      interrupted: { r: 255, g: 180, b: 50,  a: 0.9 },
    },
  };

  // ── 状态 ──
  let state = {
    mode: 'idle',          // 当前模式
    angleX: 0, angleY: 0,  // 旋转角
    amplitude: 0,          // 当前振幅 (0-1)
    speaking: false,
    ducking: false,         // 正在降低音量
    sustainedFrom: 0,       // 持续高振幅起始时间
    interrupted: false,
    animId: null,
  };

  let points = [];       // Fibonacci 点集
  let canvas, ctx, panel;
  let width = 0, height = 0;
  let interval = null;
  let streamData = [];   // 累积振幅历史

  // ── 初始化 ──
  function init(containerId) {
    panel = document.getElementById(containerId);
    if (!panel) {
      console.warn('VoicePanel: container not found');
      return;
    }

    canvas = panel.querySelector('canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'voice-canvas';
      panel.appendChild(canvas);
    }
    ctx = canvas.getContext('2d');
    resize();
    generateFibPoints(CONFIG.count);
    bindEvents();
    startAnim();
  }

  function resize() {
    width = panel.clientWidth || 260;
    height = panel.clientHeight || 260;
    canvas.width = width * devicePixelRatio;
    canvas.height = height * devicePixelRatio;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);
  }

  // ── Fibonacci 球面采样 ──
  function generateFibPoints(n) {
    points = [];
    const phi = Math.PI * (3 - Math.sqrt(5));  // 黄金角
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / (n - 1)) * 2;          // -1 → 1
      const r = Math.sqrt(1 - y * y);
      const theta = phi * i;
      points.push({
        x: Math.cos(theta) * r,
        y: y,
        z: Math.sin(theta) * r,
        origX: Math.cos(theta) * r,
        origY: y,
        origZ: Math.sin(theta) * r,
      });
    }
  }

  // ── 3D → 2D 投影 ──
  function project(p, angleX, angleY) {
    const cx = Math.cos(angleX), sx = Math.sin(angleX);
    const cy = Math.cos(angleY), sy = Math.sin(angleY);
    // 绕 Y 轴
    const x1 = p.origX * cy + p.origZ * sy;
    const y1 = p.origY;
    const z1 = -p.origX * sy + p.origZ * cy;
    // 绕 X 轴
    const x2 = x1;
    const y2 = y1 * cx - z1 * sx;
    const z2 = y1 * sx + z1 * cx;

    const scale = CONFIG.radius * 0.9;
    return {
      sx: x2 * scale + width / 2,
      sy: y2 * scale + height / 2,
      z: z2 / CONFIG.radius + 0.5,  // 用于 depth sort
    };
  }

  // ── 获取当前颜色 ──
  function getColor(mode, amplitude) {
    const c = CONFIG.stateColors[mode] || CONFIG.stateColors.idle;
    const pulse = Math.sin(Date.now() / 200) * 0.1 + 0.9;
    const amp = amplitude || 0;
    return {
      r: Math.round(c.r + amp * 50),
      g: Math.round(c.g - amp * 20),
      b: Math.round(c.b + amp * 30),
      a: c.a * pulse,
    };
  }

  // ── 绘制 ──
  function draw() {
    ctx.clearRect(0, 0, width, height);

    // 更新旋转
    state.angleX += CONFIG.rotation.x;
    state.angleY += CONFIG.rotation.y;

    const color = getColor(state.mode, state.amplitude);
    const projected = points.map(p => ({
      ...project(p, state.angleX, state.angleY),
    }));
    // 按 z 排序
    projected.sort((a, b) => a.z - b.z);

    // 点云球体 halo
    if (state.mode !== 'idle') {
      const grad = ctx.createRadialGradient(
        width / 2, height / 2, 0,
        width / 2, height / 2, CONFIG.radius * 1.2
      );
      grad.addColorStop(0, `rgba(${color.r},${color.g},${color.b},${color.a * 0.12})`);
      grad.addColorStop(0.5, `rgba(${color.r},${color.g},${color.b},${color.a * 0.05})`);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, CONFIG.radius * 1.2, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
    }

    for (const p of projected) {
      const depthAlpha = p.z * 0.4 + 0.3;
      const size = 1.5 + p.z * 1.5;
      const alpha = color.a * depthAlpha;

      ctx.beginPath();
      ctx.arc(p.sx, p.sy, size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color.r},${color.g},${color.b},${alpha})`;
      ctx.fill();
    }

    // 振幅波环
    if (state.amplitude > 0.1) {
      const ringR = CONFIG.radius * 0.8 + state.amplitude * 40;
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, ringR, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${color.r},${color.g},${color.b},${0.15 * state.amplitude})`;
      ctx.lineWidth = 1 + state.amplitude * 2;
      ctx.stroke();
    }

    state.animId = requestAnimationFrame(draw);
  }

  function startAnim() {
    if (state.animId) cancelAnimationFrame(state.animId);
    draw();
  }

  // ── 状态切换 ──
  function setMode(mode) {
    state.mode = mode;
    panel?.classList.remove('idle', 'listening', 'thinking', 'speaking', 'error', 'interrupted');
    panel?.classList.add(mode);

    // 更新标签
    const labels = {
      idle: '待机中', listening: '聆听中…',
      thinking: '思考中', speaking: '朗读中…',
      error: '语音错误', interrupted: '已打断',
    };
    const l = document.getElementById('voiceLabel');
    if (l) l.textContent = labels[mode] || mode;
  }

  // ── 振幅更新 (用于 Web Audio API 分析) ──
  function updateAmplitude(amp) {
    state.amplitude = Math.min(1, Math.max(0, amp));
    streamData.push(amp);
    if (streamData.length > 100) streamData.shift();

    // 两阶段打断检测
    if (state.mode === 'speaking' || state.mode === 'thinking') {
      if (amp > CONFIG.duckThreshold) {
        if (!state.sustainedFrom) {
          state.sustainedFrom = Date.now();
          if (!state.ducking) {
            state.ducking = true;
            // 第一阶段: duck (降音量)
            duckVolume();
          }
        } else if (Date.now() - state.sustainedFrom > CONFIG.sustainMs) {
          // 第二阶段: 完全打断
          interrupt();
        }
      } else {
        state.sustainedFrom = 0;
        if (state.ducking) {
          state.ducking = false;
          // 自动恢复
          setTimeout(() => {
            if (!state.ducking) restoreVolume();
          }, CONFIG.recoveryMs);
        }
      }
    }
  }

  function duckVolume() {
    setMode('interrupted');
    // 降低浏览器 TTS 音量
    if (window._atlasUtterance) {
      window._atlasUtterance.volume = Math.max(0.1, window._atlasUtterance.volume - 0.3);
    }
  }

  function restoreVolume() {
    if (window._atlasUtterance) {
      window._atlasUtterance.volume = 1.0;
    }
    if (state.mode === 'interrupted') {
      setMode('speaking');
    }
  }

  function interrupt() {
    state.interrupted = true;
    setMode('interrupted');
    // 停止 TTS
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    state.sustainedFrom = 0;
    state.ducking = false;
    // 标记中断
    AtlasStream.add('🔊 语音输出已打断');
    // 延迟恢复
    setTimeout(() => {
      if (state.mode === 'interrupted') {
        state.interrupted = false;
        setMode('idle');
      }
    }, 2000);
  }

  // ── TTS 说话 (Web Speech API) ──
  function speak(text, lang) {
    if (!window.speechSynthesis) {
      console.warn('VoicePanel: speechSynthesis not available');
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang || 'zh-CN';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    window._atlasUtterance = utterance;

    utterance.onstart = () => { setMode('speaking'); };
    utterance.onend = () => {
      window._atlasUtterance = null;
      if (!state.interrupted) setMode('idle');
    };
    utterance.onerror = () => {
      window._atlasUtterance = null;
      setMode('error');
      setTimeout(() => setMode('idle'), 1500);
    };

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  // ── 停止 ──
  function stop() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setMode('idle');
    state.amplitude = 0;
    state.sustainedFrom = 0;
    state.ducking = false;
    state.interrupted = false;
  }

  // ── 事件 ──
  function bindEvents() {
    window.addEventListener('resize', resize);
  }

  // ── 销毁 ──
  function destroy() {
    if (state.animId) cancelAnimationFrame(state.animId);
    if (interval) clearInterval(interval);
    window.speechSynthesis?.cancel();
  }

  return {
    init, setMode, updateAmplitude, speak, stop, destroy,
  };
})();
