import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
let backendProcess = null
function getBackendPath() {
  // 开发环境路径
  const devBackendPath = path.join(__dirname, '../backend')
  if (fs.existsSync(devBackendPath)) {
    return devBackendPath
  }
  // 打包后路径，在resources目录下
  const prodBackendPath = path.join(process.resourcesPath, 'backend')
  return prodBackendPath
}
function getPythonPath() {
  // 优先使用用户环境变量中的Python
  const pythonPath = process.env.PYTHON_PATH || 'python'
  // 检查是否存在打包后的嵌入式Python（后续可添加）
  return pythonPath
}
export async function startBackendServer() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath()
    const pythonPath = getPythonPath()
    console.log('后端路径:', backendPath)
    console.log('Python路径:', pythonPath)
    // 启动FastAPI服务，uvicorn作为ASGI服务器
    const process = spawn(
      pythonPath,
      ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1'],
      {
        cwd: backendPath,
        env: {
          ...process.env,
          PYTHONPATH: backendPath,
          NODE_ENV: process.env.NODE_ENV || 'production'
        },
        stdio: ['ignore', 'pipe', 'pipe']
      }
    )
    // 监听输出，判断服务是否启动成功
    let started = false
    process.stdout.on('data', (data) => {
      const output = data.toString()
      console.log('后端输出:', output)
      if (output.includes('Application startup complete') || output.includes('Uvicorn running on')) {
        if (!started) {
          started = true
          resolve(process)
        }
      }
    })
    process.stderr.on('data', (data) => {
      const error = data.toString()
      console.error('后端错误:', error)
      if (error.includes('address already in use') || error.includes('端口被占用')) {
        if (!started) {
          started = true
          resolve(process)
        }
      }
    })
    process.on('error', (error) => {
      console.error('启动后端服务失败:', error)
      if (!started) {
        reject(error)
      }
    })
    process.on('exit', (code, signal) => {
      console.log(`后端服务退出，代码: ${code}, 信号: ${signal}`)
      backendProcess = null
    })
    // 超时处理
    setTimeout(() => {
      if (!started) {
        reject(new Error('启动后端服务超时'))
      }
    }, 30000) // 30秒超时
    backendProcess = process
  })
}
export function stopBackendServer(process) {
  if (process && !process.killed) {
    try {
      // Windows下杀死整个进程树
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', process.pid, '/f', '/t'])
      } else {
        process.kill('SIGTERM')
      }
      console.log('后端服务已停止')
    } catch (error) {
      console.error('停止后端服务失败:', error)
    }
  }
  backendProcess = null
}
export function isBackendRunning(process) {
  return process && !process.killed
}
