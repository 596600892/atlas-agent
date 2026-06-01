/**
 * Atlas Agent — Electron Desktop App (Tray + Shortcuts)
 * =========================================================
 * 主进程: 托盘图标 + 全局快捷键 + 窗口管理
 *
 * 启动方式:
 *   1. 先启动 Atlas WebUI 服务器 (uv run python webui/app.py --port 8645)
 *   2. 然后运行: npx electron webui/electron/main.js
 *
 * 或使用 ATLAS_AUTO_START=1 自动启动后端
 */

const { app, BrowserWindow, dialog, shell, Tray, Menu, globalShortcut, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// ── 配置 ────────────────────────────────────

const WEBUI_URL = process.env.ATLAS_WEB_URL || 'http://127.0.0.1:8645';
const AUTO_START = process.env.ATLAS_AUTO_START === '1';

let mainWindow = null;
let tray = null;
let serverProcess = null;

// ── 后端管理 ────────────────────────────────

function startBackend() {
  return new Promise((resolve, reject) => {
    serverProcess = spawn('uv', ['run', 'python', 'webui/app.py', '--port', '8645'], {
      cwd: path.join(__dirname, '..'),
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, ATLAS_LOG_LEVEL: 'WARNING' },
    });

    serverProcess.stdout.on('data', (data) => {
      const text = data.toString();
      console.log('[atlas]', text);
      if (text.includes('Running on')) resolve();
    });

    serverProcess.stderr.on('data', (data) => {
      console.error('[atlas:err]', data.toString());
    });

    serverProcess.on('error', (err) => reject(err));
    // 15 秒超时
    setTimeout(() => resolve(), 15000);
  });
}

function stopBackend() {
  if (serverProcess) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

// ── 托盘图标 ───────────────────────────────

function createTray() {
  // 用原生图标创建托盘
  const iconSize = process.platform === 'darwin' ? 16 : 22;
  const icon = nativeImage.createEmpty();
  // macOS 需要模板图标
  const iconPath = path.join(__dirname, 'icon.png');
  try {
    tray = new Tray(iconPath);
  } catch {
    // Fallback：创建简单 canvas 图标
    tray = new Tray(nativeImage.createFromBuffer(
      Buffer.alloc(iconSize * iconSize * 4, 0), { width: iconSize, height: iconSize }
    ));
  }

  tray.setToolTip('Atlas Agent');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示/隐藏 Atlas',
      click: () => toggleWindow(),
    },
    { type: 'separator' },
    {
      label: `端口 ${WEBUI_URL.match(/:(\d+)/)?.[1] || '8645'}`,
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '重启后端',
      click: () => {
        stopBackend();
        setTimeout(() => startBackend().catch(console.error), 1000);
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => toggleWindow());
}

// ── 窗口切换 ───────────────────────────────

function toggleWindow() {
  if (mainWindow) {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  }
}

// ── 全局快捷键 ─────────────────────────────

function registerShortcuts() {
  // Ctrl+Shift+A: 显示/隐藏
  globalShortcut.register('CommandOrControl+Shift+A', () => toggleWindow());

  // Ctrl+Shift+R: 刷新
  globalShortcut.register('CommandOrControl+Shift+R', () => {
    if (mainWindow) mainWindow.webContents.reload();
  });

  // Ctrl+Shift+Q: 退出
  globalShortcut.register('CommandOrControl+Shift+Q', () => {
    app.isQuitting = true;
    app.quit();
  });
}

// ── 窗口创建 ────────────────────────────────

function createWindow() {
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: sw, height: sh } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1400, sw - 40),
    height: Math.min(900, sh - 40),
    minWidth: 800,
    minHeight: 600,
    title: 'Atlas Agent',
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false, // 先不显示，等 ready
  });

  mainWindow.loadURL(WEBUI_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 关闭到托盘而不是退出
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  // 打开外部链接到系统浏览器
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── 生命周期 ────────────────────────────────

app.isQuitting = false;

app.whenReady().then(async () => {
  if (AUTO_START) {
    try {
      console.log('[Atlas] 启动后端...');
      await startBackend();
      console.log('[Atlas] 后端就绪');
    } catch (e) {
      dialog.showErrorBox('启动错误', `后端启动失败:\n${e.message}\n\n请手动启动:\nuv run python webui/app.py --port 8645`);
    }
  }

  createWindow();
  createTray();
  registerShortcuts();

  console.log(`[Atlas] WebUI: ${WEBUI_URL}`);
  console.log('[Atlas] 快捷键: Ctrl+Shift+A 切换 · Ctrl+Shift+R 刷新 · Ctrl+Shift+Q 退出');

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  // macOS 不自动退出
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  globalShortcut.unregisterAll();
  stopBackend();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
