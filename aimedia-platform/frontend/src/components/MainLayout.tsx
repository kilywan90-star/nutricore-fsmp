import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, theme } from 'antd'
import {
  FileTextOutlined, AuditOutlined, SendOutlined,
  DashboardOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout

export function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()

  const menuItems = [
    { key: '/content', icon: <FileTextOutlined />, label: '内容管理' },
    { key: '/review', icon: <AuditOutlined />, label: '审核管理' },
    { key: '/publish', icon: <SendOutlined />, label: '发布管理' },
    { key: '/dashboard', icon: <DashboardOutlined />, label: '数据分析' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}
             style={{ background: token.colorBgContainer }}>
        <div style={{ height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 700, fontSize: collapsed ? 14 : 18, borderBottom: '1px solid #f0f0f0' }}>
          {collapsed ? '融媒' : 'AI融媒体平台'}
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]}
              items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ background: token.colorBgContainer, padding: '0 24px',
                         display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                  onClick={() => setCollapsed(!collapsed)} />
          <Button type="text" icon={<LogoutOutlined />}>退出</Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
