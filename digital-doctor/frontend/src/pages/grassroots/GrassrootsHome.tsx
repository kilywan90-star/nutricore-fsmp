import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Button, Spin, Typography } from 'antd';
import {
  FormOutlined,
  HeartOutlined,
  AlertOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { getGrassrootsDashboard, type GrassrootsDashboardData } from '../../lib/api';

const { Title } = Typography;

export default function GrassrootsHome() {
  const nav = useNavigate();
  const [data, setData] = useState<GrassrootsDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const result = await getGrassrootsDashboard();
      setData(result);
    } catch {
      // Offline mode — show empty dashboard
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>今日概览</Title>

      <Row gutter={[12, 12]}>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="今日筛查"
              value={data?.today_screenings ?? 0}
              valueStyle={{ fontSize: 28 }}
              prefix={<FormOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="本月筛查"
              value={data?.screenings_this_month ?? 0}
              valueStyle={{ fontSize: 28 }}
              prefix={<FormOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="高危患者"
              value={data?.high_risk_count ?? 0}
              valueStyle={{ fontSize: 28, color: '#ff4d4f' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="待随访"
              value={data?.overdue_follow_ups ?? 0}
              valueStyle={{ fontSize: 28, color: data?.overdue_follow_ups ? '#faad14' : undefined }}
              prefix={<HeartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="管理总数"
              value={data?.total_managed ?? 0}
              valueStyle={{ fontSize: 28 }}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="待转诊"
              value={data?.pending_referrals ?? 0}
              valueStyle={{ fontSize: 28, color: data?.pending_referrals ? '#ff4d4f' : undefined }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>快捷操作</Title>
      <Row gutter={[12, 12]}>
        <Col span={12}>
          <Button
            type="primary"
            size="large"
            block
            icon={<FormOutlined />}
            onClick={() => nav('/grassroots/screening')}
            style={{ height: 60, fontSize: 16 }}
          >
            新筛查登记
          </Button>
        </Col>
        <Col span={12}>
          <Button
            size="large"
            block
            icon={<HeartOutlined />}
            onClick={() => nav('/grassroots/follow-up')}
            style={{ height: 60, fontSize: 16 }}
          >
            开始随访
          </Button>
        </Col>
      </Row>
    </div>
  );
}
