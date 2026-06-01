/* Atlas — Hotspot Earth (3D 地球热点)
   Three.js 程序化地球 + 云层 + 大气辉光 + 城市标记 + 跑马灯
   基于 BaiLongma 设计思想，纯前端，零后端API依赖
   ──────────────────────────────────────────────────── */

const AtlasHotspot = (() => {
  'use strict';

  const CITIES = [
    { name: '纽约', lat: 40.7, lng: -74.0, heat: 0.9 },
    { name: '伦敦', lat: 51.5, lng: -0.1, heat: 0.8 },
    { name: '东京', lat: 35.7, lng: 139.7, heat: 0.85 },
    { name: '上海', lat: 31.2, lng: 121.5, heat: 0.75 },
    { name: '香港', lat: 22.3, lng: 114.2, heat: 0.7 },
    { name: '新加坡', lat: 1.35, lng: 103.8, heat: 0.65 },
    { name: '迪拜', lat: 25.2, lng: 55.3, heat: 0.6 },
    { name: '悉尼', lat: -33.9, lng: 151.2, heat: 0.5 },
    { name: '莫斯科', lat: 55.8, lng: 37.6, heat: 0.55 },
    { name: '旧金山', lat: 37.8, lng: -122.4, heat: 0.7 },
    { name: '柏林', lat: 52.5, lng: 13.4, heat: 0.6 },
    { name: '首尔', lat: 37.6, lng: 127.0, heat: 0.65 },
    { name: '班加罗尔', lat: 12.9, lng: 77.6, heat: 0.55 },
    { name: '圣保罗', lat: -23.5, lng: -46.6, heat: 0.45 },
    { name: '开普敦', lat: -33.9, lng: 18.4, heat: 0.35 },
  ];

  // 跑马灯数据源
  const TICKER_SOURCES = [
    { icon: '📰', label: '新闻' },
    { icon: '🐦', label: '社交' },
    { icon: '📊', label: '财经' },
    { icon: '💻', label: '技术' },
  ];

  let scene, camera, renderer;
  let earth, cloudLayer, glowSprite;
  let cityMarkers = [];
  let autoRotate = true;
  let container, canvasEl;
  let tickerItems = [];
  let mounted = false;

  // ── 经纬度 → 3D 坐标 ──
  function latLngToVector3(lat, lng, radius) {
    const phi = (90 - lat) * Math.PI / 180;
    const theta = (lng + 180) * Math.PI / 180;
    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  }

  // ── 程序化地球纹理 ──
  function createEarthTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    // 海洋底色
    const grad = ctx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0, '#1a2a4a');
    grad.addColorStop(0.3, '#1e3a5f');
    grad.addColorStop(0.5, '#1a3a5a');
    grad.addColorStop(0.7, '#1e3a5f');
    grad.addColorStop(1, '#1a2a4a');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 512);

    // 大陆块 (简化形状)
    const continents = [
      // North America
      [[2.0,0.23],[2.15,0.2],[2.3,0.18],[2.4,0.22],[2.45,0.28],[2.4,0.32],[2.35,0.38],[2.3,0.4],[2.25,0.42],[2.15,0.4],[2.1,0.38],[2.05,0.35],[2.0,0.32]],
      // South America
      [[2.25,0.48],[2.35,0.46],[2.4,0.48],[2.42,0.52],[2.4,0.56],[2.35,0.6],[2.3,0.62],[2.25,0.6],[2.2,0.56],[2.2,0.52]],
      // Europe
      [[0.55,0.3],[0.6,0.28],[0.65,0.28],[0.68,0.3],[0.67,0.33],[0.65,0.35],[0.6,0.36],[0.55,0.35],[0.53,0.33]],
      // Africa
      [[0.55,0.38],[0.6,0.37],[0.65,0.37],[0.68,0.39],[0.7,0.42],[0.68,0.48],[0.65,0.52],[0.6,0.54],[0.55,0.52],[0.52,0.48],[0.5,0.44],[0.5,0.4]],
      // Asia (large block)
      [[0.65,0.2],[0.7,0.18],[0.75,0.17],[0.8,0.18],[0.85,0.2],[0.88,0.22],[0.9,0.25],[0.88,0.28],[0.85,0.3],[0.82,0.32],[0.78,0.33],[0.72,0.33],[0.68,0.31],[0.65,0.28],[0.63,0.25]],
      // Southeast Asia / Oceania
      [[0.88,0.38],[0.92,0.37],[0.95,0.38],[0.94,0.4],[0.92,0.42],[0.88,0.41],[0.86,0.4]],
      [[0.98,0.5],[1.0,0.49],[1.02,0.5],[1.01,0.52],[0.99,0.53],[0.97,0.52]],
    ];

    ctx.fillStyle = 'rgba(40, 80, 50, 0.7)';
    for (const pts of continents) {
      ctx.beginPath();
      const s = pts.map(p => [p[0] * 1024, p[1] * 512]);
      ctx.moveTo(s[0][0], s[0][1]);
      for (let i = 1; i < s.length; i++) {
        ctx.lineTo(s[i][0], s[i][1]);
      }
      ctx.closePath();
      ctx.fill();

      // 大陆边缘高光
      ctx.strokeStyle = 'rgba(70, 140, 80, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // 细小点缀
    for (let i = 0; i < 200; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 512;
      ctx.fillStyle = `rgba(50, 100, 60, ${0.1 + Math.random() * 0.15})`;
      ctx.beginPath();
      ctx.arc(x, y, 1 + Math.random() * 2, 0, Math.PI * 2);
      ctx.fill();
    }

    return new THREE.CanvasTexture(canvas);
  }

  // ── 云层纹理 ──
  function createCloudTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.fillRect(0, 0, 512, 256);

    for (let i = 0; i < 300; i++) {
      const x = Math.random() * 512;
      const y = Math.random() * 256;
      const r = 5 + Math.random() * 20;
      const a = 0.05 + Math.random() * 0.15;
      ctx.fillStyle = `rgba(255,255,255,${a})`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    return new THREE.CanvasTexture(canvas);
  }

  // ── 初始化 ──
  function init(containerEl) {
    if (!containerEl) return;
    if (mounted) return;

    container = containerEl;
    const rect = container.getBoundingClientRect();
    const w = rect.width || 300;
    const h = rect.height || 200;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(0, 0, 4);

    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
    });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.domElement.style.position = 'absolute';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    container.appendChild(renderer.domElement);
    canvasEl = renderer.domElement;

    // 地球
    const earthGeo = new THREE.SphereGeometry(1.5, 48, 48);
    const earthMat = new THREE.MeshPhongMaterial({
      map: createEarthTexture(),
      specular: new THREE.Color(0x333333),
      shininess: 5,
    });
    earth = new THREE.Mesh(earthGeo, earthMat);
    scene.add(earth);

    // 云层
    const cloudGeo = new THREE.SphereGeometry(1.52, 32, 32);
    const cloudMat = new THREE.MeshPhongMaterial({
      map: createCloudTexture(),
      transparent: true,
      opacity: 0.25,
      depthWrite: false,
    });
    cloudLayer = new THREE.Mesh(cloudGeo, cloudMat);
    scene.add(cloudLayer);

    // 城市标记
    for (const city of CITIES) {
      const pos = latLngToVector3(city.lat, city.lng, 1.55);
      const marker = createCityMarker(pos, city.heat);
      cityMarkers.push(marker);
      scene.add(marker);
    }

    // 大气辉光 (sprite)
    const glowCanvas = document.createElement('canvas');
    glowCanvas.width = 128;
    glowCanvas.height = 128;
    const gctx = glowCanvas.getContext('2d');
    const grad2 = gctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad2.addColorStop(0, 'rgba(60, 160, 255, 0.3)');
    grad2.addColorStop(0.5, 'rgba(60, 160, 255, 0.08)');
    grad2.addColorStop(1, 'rgba(0,0,0,0)');
    gctx.fillStyle = grad2;
    gctx.fillRect(0, 0, 128, 128);
    glowSprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(glowCanvas),
      blending: THREE.AdditiveBlending,
    }));
    glowSprite.scale.set(6, 6, 1);
    glowSprite.position.set(0, 0, 0);
    scene.add(glowSprite);

    // 灯光
    const ambient = new THREE.AmbientLight(0x404060);
    scene.add(ambient);
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(3, 2, 4);
    scene.add(dirLight);
    const fillLight = new THREE.DirectionalLight(0x4488ff, 0.4);
    fillLight.position.set(-3, -1, -2);
    scene.add(fillLight);

    // 星空背景
    const starsGeo = new THREE.BufferGeometry();
    const starPos = new Float32Array(2000 * 3);
    for (let i = 0; i < 2000 * 3; i++) starPos[i] = (Math.random() - 0.5) * 200;
    starsGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starsMat = new THREE.PointsMaterial({
      color: 0x88aaff,
      size: 0.08,
      transparent: true,
      opacity: 0.6,
    });
    const stars = new THREE.Points(starsGeo, starsMat);
    scene.add(stars);

    // 加载跑马灯数据
    loadTickerData();

    // 开始渲染循环
    animate();
    mounted = true;
  }

  // ── 城市标记 (光柱+光环) ──
  function createCityMarker(position, heat) {
    const group = new THREE.Group();
    group.position.copy(position);

    // 光柱 (细长圆柱)
    const pillarGeo = new THREE.CylinderGeometry(0.01, 0.02, 0.1 + heat * 0.15, 4);
    const pillarMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color().setHSL(0.55 + heat * 0.15, 0.8, 0.5 + heat * 0.3),
      transparent: true,
      opacity: 0.6 + heat * 0.4,
    });
    const pillar = new THREE.Mesh(pillarGeo, pillarMat);
    pillar.position.set(0, 0.05 + heat * 0.08, 0);
    group.add(pillar);

    // 光环 (小圆环)
    const ringMat = new THREE.SpriteMaterial({
      color: new THREE.Color().setHSL(0.55 + heat * 0.15, 0.8, 0.6),
      transparent: true,
      opacity: 0.4 * heat,
    });
    const ring = new THREE.Sprite(ringMat);
    ring.scale.set(0.04, 0.04, 1);
    group.add(ring);

    // 底部光点
    const dotMat = new THREE.SpriteMaterial({
      map: createDotTexture(),
      blending: THREE.AdditiveBlending,
      transparent: true,
    });
    const dot = new THREE.Sprite(dotMat);
    dot.scale.set(0.03, 0.03, 1);
    group.add(dot);

    return group;
  }

  function createDotTexture() {
    const c = document.createElement('canvas');
    c.width = 16; c.height = 16;
    const ctx = c.getContext('2d');
    const g = ctx.createRadialGradient(8, 8, 0, 8, 8, 8);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.3, 'rgba(100,200,255,0.6)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 16, 16);
    return new THREE.CanvasTexture(c);
  }

  // ── 跑马灯数据 ──
  function loadTickerData() {
    const tickerEl = document.getElementById('hotspotTicker');
    if (!tickerEl) return;

    tickerItems = [];
    for (let s = 0; s < 3; s++) {
      for (const src of TICKER_SOURCES) {
        tickerItems.push({
          icon: src.icon,
          text: `${src.label} · 热门话题 #${s + 1}`,
        });
      }
    }

    // 更新跑马灯
    updateTicker(tickerEl);
  }

  function updateTicker(el) {
    if (!el) return;
    const items = tickerItems.map(t =>
      `<span class="ticker-item"><span class="ticker-icon">${t.icon}</span>${t.text}</span>`
    ).join(' <span class="ticker-sep">◆</span> ');
    el.innerHTML = `<span class="ticker-inner">${items}</span>`;
    // 动画跑马灯通过 CSS animation 实现
  }

  // ── 渲染循环 ──
  function animate() {
    requestAnimationFrame(animate);

    if (autoRotate) {
      earth.rotation.y += 0.002;
      cloudLayer.rotation.y += 0.001;

      // 城市标记脉冲动画
      const t = Date.now() / 1000;
      cityMarkers.forEach((marker, i) => {
        const pulse = Math.sin(t * 2 + i * 0.5) * 0.3 + 0.7;
        marker.children.forEach(child => {
          if (child.material) {
            child.material.opacity = child.material.opacity * 0.9 + pulse * 0.1;
          }
          if (child.isSprite) {
            const s = 0.03 + pulse * 0.02;
            child.scale.set(s, s, 1);
          }
        });
      });
    }

    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  // ── 切换显示 ──
  function toggle() {
    const panel = document.getElementById('hotspotPanel');
    if (!panel) return;
    const isHidden = panel.hidden;
    panel.hidden = !isHidden;

    if (isHidden) {
      // 显示：需要初始化
      const container = document.querySelector('.hotspot-earth-scene');
      if (container && !mounted) {
        init(container);
      }
      // 延迟 resize 以确保尺寸正确
      setTimeout(resize, 100);
    }
  }

  // ── 调整大小 ──
  function resize() {
    const panel = document.getElementById('hotspotPanel');
    if (!panel || panel.hidden) return;
    const container = document.querySelector('.hotspot-earth-scene');
    if (!container || !renderer) return;
    const w = window.innerWidth;
    const h = 280;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  // ── 销毁 ──
  function destroy() {
    mounted = false;
    if (renderer) {
      renderer.dispose();
      renderer.domElement.remove();
    }
    scene = null;
    camera = null;
    renderer = null;
    earth = null;
    cloudLayer = null;
    cityMarkers = [];
  }

  return { init, toggle, resize, destroy };
})();
