import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Typography, Badge } from 'antd';
import {
  HomeOutlined,
  FormOutlined,
  HeartOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { Footer } = Layout;

const tabs = [
  { key: '/grassroots', icon: <HomeOutlined />, label: '首页' },
  { key: '/grassroots/screening', icon: <FormOutlined />, label: '筛查' },
  { key: '/grassroots/follow-up', icon: <HeartOutlined />, label: '随访' },
  { key: '/grassroots/patients', icon: <TeamOutlined />, label: '患者' },
];

export default function GrassrootsLayout() {
  const nav = useNavigate();
  const loc = useLocation();
  const [offline, setOffline] = useState(!navigator.onLine);

  // Listen for online/offline events
  if (typeof window !== 'undefined') {
    window.ononline = () => setOffline(false);
    window.onoffline = () => setOffline(true);
  }

  const activeKey = tabs.find((t) => loc.pathname.startsWith(t.key))?.key || '/grassroots';

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* Header */}
      <div
        style={{
          background: '#1677ff',
          padding: '12px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: '#fff',
        }}
      >
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
          基层慢病管理
        </Typography.Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Badge status={offline ? 'error' : 'success'} />
          <span style={{ fontSize: 12 }}>{offline ? '离线' : '在线'}</span>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: 16, paddingBottom: 64 }}>
        <Outlet />
      </div>

      {/* Bottom Tab Bar */}
      <Footer
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          padding: 0,
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
          zIndex: 100,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-around', height: 56 }}>
          {tabs.map((tab) => (
            <div
              key={tab.key}
              onClick={() => nav(tab.key)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: activeKey === tab.key ? '#1677ff' : '#999',
                fontSize: 20,
                minHeight: 56,
                minWidth: 56,
              }}
            >
              {tab.icon}
              <span style={{ fontSize: 10, marginTop: 2 }}>{tab.label}</span>
            </div>
          ))}
        </div>
      </Footer>
    </Layout>
  );
}
