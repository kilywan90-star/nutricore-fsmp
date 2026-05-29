import React, { useState, useEffect } from 'react'
import { Layout, Menu, Button, message, Spin } from 'antd'
import {
  FileTextOutlined,
  BookOutlined,
  FileCopyOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UnfoldOutlined,
  FoldOutlined
} from '@ant-design/icons'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { HashRouter } from 'react-router-dom'
import ProjectList from './pages/project/ProjectList'
import KnowledgeList from './pages/knowledge/KnowledgeList'
import TemplateList from './pages/template/TemplateList'
import Settings from './pages/settings/Settings'
import Editor from './pages/editor/Editor'
import './App.css'
const { Sider, Content, Header } = Layout
function AppContent() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [backendStatus, setBackendStatus] = useState<'checking' | 'running' | 'error'>('checking')
  useEffect(() => {
    checkBackendStatus()
  }, [])
  const checkBackendStatus = async () => {
    try {
      const isRunning = await window.electronAPI.isBackendRunning()
      setBackendStatus(isRunning ? 'running' : 'error')
      if (isRunning) {
        message.success('后端服务连接正常')
      } else {
        message.error('后端服务连接失败，请重启应用')
      }
    } catch (error) {
      console.error('检查后端状态失败:', error)
      setBackendStatus('error')
      message.error('检查后端状态失败')
    }
  }
  const menuItems = [
    {
      key: '/project',
      icon: <FileTextOutlined />,
      label: '项目管理',
      onClick: () => navigate('/project')
    },
    {
      key: '/knowledge',
      icon: <BookOutlined />,
      label: '知识库',
      onClick: () => navigate('/knowledge')
    },
    {
      key: '/template',
      icon: <FileCopyOutlined />,
      label: '模板管理',
      onClick: () => navigate('/template')
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => navigate('/settings')
    }
  ]
  const selectedKey = location.pathname.startsWith('/editor') ? '/project' : location.pathname
  if (backendStatus === 'checking') {
    return (
      <div style={{
        width: '100%',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fff'
      }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, fontSize: 16 }}>正在启动服务，请稍候...</div>
      </div>
    )
  }
  return (
    <Layout style={{ height: '100%' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        style={{ background: '#001529' }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 16px',
          color: '#fff',
          fontSize: collapsed ? 16 : 18,
          fontWeight: 'bold',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          {collapsed ? '标书' : '智能标书生成'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          style={{ border: 'none' }}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 16px',
          background: '#fff',
          borderBottom: '1px solid #e8e8e8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <Button
            type="text"
            icon={collapsed ? <UnfoldOutlined /> : <FoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {backendStatus === 'running' ? (
                <>
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <span style={{ color: '#52c41a', fontSize: 12 }}>服务正常</span>
                </>
              ) : (
                <>
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  <span style={{ color: '#ff4d4f', fontSize: 12 }}>服务异常</span>
                </>
              )}
            </div>
          </div>
        </Header>
        <Content style={{ overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={<ProjectList />} />
            <Route path="/project" element={<ProjectList />} />
            <Route path="/editor/:projectId" element={<Editor />} />
            <Route path="/knowledge" element={<KnowledgeList />} />
            <Route path="/template" element={<TemplateList />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}
function App() {
  return (
    <HashRouter>
      <AppContent />
    </HashRouter>
  )
}
export default App
