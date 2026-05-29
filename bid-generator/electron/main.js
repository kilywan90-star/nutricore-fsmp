import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { startBackendServer, stopBackendServer, isBackendRunning } from './server-manager.js'
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
let mainWindow = null
let backendProcess = null
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: '智能标书生成工具',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true
    },
    show: false
  })
  // 开发环境加载Vite开发服务器地址，生产环境加载打包后的静态文件
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    // 开发环境默认打开开发者工具
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
    mainWindow.focus()
  })
  mainWindow.on('closed', () => {
    mainWindow = null
  })
}
// 应用程序准备完成时执行
app.whenReady().then(async () => {
  try {
    // 先启动后端服务
    backendProcess = await startBackendServer()
    console.log('后端服务启动成功')
    // 创建主窗口
    createWindow()
  } catch (error) {
    console.error('启动失败:', error)
    app.quit()
  }
  app.on('activate', () => {
    // 在macOS上，当单击dock图标并且没有其他窗口打开时，通常重新创建一个窗口
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})
// 当所有窗口关闭时退出应用，除了macOS
app.on('window-all-closed', () => {
  // 先停止后端服务
  if (backendProcess) {
    stopBackendServer(backendProcess)
  }
  if (process.platform !== 'darwin') app.quit()
})
// 退出前清理资源
app.on('before-quit', (event) => {
  if (backendProcess && isBackendRunning(backendProcess)) {
    event.preventDefault()
    stopBackendServer(backendProcess)
    setTimeout(() => {
      app.exit()
    }, 1000)
  }
})
// IPC通信处理
ipcMain.handle('get-backend-url', () => {
  return 'http://localhost:8000'
})
ipcMain.handle('is-backend-running', () => {
  return isBackendRunning(backendProcess)
})
