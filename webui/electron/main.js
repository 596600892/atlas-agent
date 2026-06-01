/**
 * Atlas Agent — Electron Desktop App
 * ====================================
 * 主进程: 创建浏览器窗口，嵌入 WebUI
 *
 * 启动方式:
 *   1. 先启动 Atlas WebUI 服务器 (atlas web)
 *   2. 然后运行: cd webui/electron && npx electron .
 *
 * 或使用开发模式自动启动后端:
 *   ATLAS_AUTO_START=1 npx electron .
 */

const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// ── 配置 ────────────────────────────────────

const WEBUI_URL = process.env.ATLAS_WEB_URL || 'http://127.0.0.1:8640';
const AUTO_START = process.env.ATLAS_AUTO_START === '1';

let mainWindow = null;
let serverProcess = null;

// ── 后端管理 ────────────────────────────────

function startBackend() {
  return new Promise((resolve, reject) => {
    const atlasBin = path.join(__dirname, '..', '..', '.venv', 'bin', 'atlas');
    // 先尝试系统路径
    serverProcess = spawn('atlas', ['web', '--port', '8640'], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, ATLAS_LOG_LEVEL: 'WARNING' },
    });

    serverProcess.stdout.on('data', (data) => {
      const text = data.toString();
      console.log('[atlas]', text);
      if (text.includes('http://')) {
        resolve();
      }
    });

    serverProcess.stderr.on('data', (data) => {
      console.error('[atlas:err]', data.toString());
    });

    serverProcess.on('error', (err) => {
      reject(err);
    });

    // 10 秒超时
    setTimeout(() => resolve(), 10000);
  });
}

function stopBackend() {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

// ── 窗口创建 ────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'Atlas Agent',
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(WEBUI_URL);

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

app.whenReady().then(async () => {
  if (AUTO_START) {
    try {
      await startBackend();
    } catch (e) {
      dialog.showErrorBox('Startup Error', `Failed to start Atlas backend:\n${e.message}`);
    }
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});
