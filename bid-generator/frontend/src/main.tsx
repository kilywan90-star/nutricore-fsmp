import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={{
      token: {
        colorPrimary: '#1890ff',
        borderRadius: 4,
        fontSize: 14
      }
    }}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
