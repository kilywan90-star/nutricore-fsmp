import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Button, List, Typography, Spin, Empty } from 'antd';
import {
  SearchOutlined,
  AlertOutlined,
  TeamOutlined,
  WarningOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getPatients, getAllAlerts, type PatientListResponse, type DoctorAlertItem } from '../../lib/api';
import AlertBadge from '../../components/AlertBadge';

const { Title } = Typography;

export default function DoctorDashboard() {
  const nav = useNavigate();
  const [patients, setPatients] = useState<PatientListResponse | null>(null);
  const [alerts, setAlerts] = useState<DoctorAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        const [patientData, alertData] = await Promise.all([
          getPatients(1, 100),
          getAllAlerts({ page_size: 10 }),
        ]);
        if (!cancelled) {
          setPatients(patientData);
          setAlerts(alertData?.items || alertData?.alerts || []);
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || '加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  if (error) {
    return <div style={{ padding: 24 }}><Empty description={error} /></div>;
  }

  const totalPatients = patients?.total ?? 0;
  const unacknowledgedAlerts = (alerts || []).filter((a: any) => !a.acknowledged).length;
  const poorControlCount = patients?.items?.filter(
    (p) => p.latest_glucose != null && p.latest_glucose > 10.0
  ).length ?? 0;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav('/patient')}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>医生工作台</Title>
      </Row>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card hoverable onClick={() => nav('/doctor/patients')}>
            <Statistic
              title="管理患者总数"
              value={totalPatients}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card hoverable onClick={() => nav('/doctor/alerts')}>
            <Statistic
              title="未读预警"
              value={unacknowledgedAlerts}
              prefix={<AlertOutlined />}
              valueStyle={{ color: unacknowledgedAlerts > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="血糖控制不佳"
              value={poorControlCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: poorControlCount > 0 ? '#faad14' : '#52c41a' }}
              suffix="人"
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card title="快捷操作" style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={() => nav('/doctor/patients')}
            >
              患者检索
            </Button>
          </Col>
          <Col>
            <Button
              icon={<AlertOutlined />}
              onClick={() => nav('/doctor/alerts')}
              danger={unacknowledgedAlerts > 0}
            >
              查看全部预警
              {unacknowledgedAlerts > 0 && ` (${unacknowledgedAlerts})`}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Recent Alerts */}
      <Card title="最近预警">
        {alerts.length === 0 ? (
          <Empty description="暂无预警" />
        ) : (
          <List
            dataSource={alerts.slice(0, 10)}
            renderItem={(item: DoctorAlertItem) => (
              <List.Item
                key={item.id}
                extra={
                  <AlertBadge severity={item.severity as 'info' | 'warning' | 'critical'}>
                    {item.severity === 'critical' ? '危急' : item.severity === 'warning' ? '预警' : '信息'}
                  </AlertBadge>
                }
                onClick={() => nav(`/doctor/patients/${item.patient_id}`)}
                style={{ cursor: 'pointer' }}
              >
                <List.Item.Meta
                  title={
                    <span>
                      {item.title}
                      {!item.acknowledged && (
                        <span style={{ color: '#ff4d4f', marginLeft: 8, fontSize: 12 }}>未确认</span>
                      )}
                    </span>
                  }
                  description={
                    <span>
                      患者: {item.patient_id?.slice(0, 8)}... | {dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}
                      <br />
                      {item.detail}
                    </span>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
