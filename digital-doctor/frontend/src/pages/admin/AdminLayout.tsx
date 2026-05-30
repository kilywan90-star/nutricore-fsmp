import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  ClusterOutlined,
  TeamOutlined,
  SettingOutlined,
  AuditOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';

const { Sider, Content, Header } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: '/admin', icon: <DashboardOutlined />, label: '概览' },
  { key: '/admin/departments', icon: <ClusterOutlined />, label: '科室管理' },
  { key: '/admin/doctors', icon: <TeamOutlined />, label: '医生管理' },
  { key: '/admin/config', icon: <SettingOutlined />, label: '参数配置' },
  { key: '/admin/audit', icon: <AuditOutlined />, label: '操作日志' },
];

export default function AdminLayout() {
  const nav = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems.find(
    (item) => location.pathname === item.key
  )?.key || '/admin';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth={60}
        width={220}
        style={{ background: '#001529' }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Title level={5} style={{ color: '#fff', margin: 0 }}>
            管理后台
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => nav(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <ArrowLeftOutlined
            style={{ cursor: 'pointer', marginRight: 16, fontSize: 16 }}
            onClick={() => nav('/doctor')}
          />
          <span style={{ fontSize: 16, fontWeight: 500 }}>
            {menuItems.find((m) => m.key === selectedKey)?.label || '管理后台'}
          </span>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5', minHeight: 360 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
