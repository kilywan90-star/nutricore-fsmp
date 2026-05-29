import { contextBridge, ipcRenderer } from 'electron'
contextBridge.exposeInMainWorld('electronAPI', {
  // 获取后端服务地址
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  // 检查后端服务是否运行
  isBackendRunning: () => ipcRenderer.invoke('is-backend-running'),
  // 打开文件选择对话框
  openFileDialog: (options) => ipcRenderer.invoke('open-file-dialog', options),
  // 打开文件夹选择对话框
  openDirectoryDialog: () => ipcRenderer.invoke('open-directory-dialog'),
  // 获取用户数据目录
  getUserDataPath: () => ipcRenderer.invoke('get-user-data-path'),
  // 打开外部链接
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  // 最小化窗口
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  // 最大化窗口
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  // 关闭窗口
  closeWindow: () => ipcRenderer.invoke('close-window'),
  // 监听后端服务状态
  onBackendStatusChanged: (callback) => {
    ipcRenderer.on('backend-status-changed', (event, status) => callback(status))
    return () => ipcRenderer.removeListener('backend-status-changed', callback)
  }
})
