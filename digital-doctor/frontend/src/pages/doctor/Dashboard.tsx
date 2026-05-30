import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Button, List, Typography, Spin, Empty, message } from 'antd';
import {
  SearchOutlined,
  AlertOutlined,
  TeamOutlined,
  WarningOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getPatients, getAllAlerts,
  listCriticalAlerts, acknowledgeCriticalAlert, getCriticalAlertStats,
  type PatientListResponse, type DoctorAlertItem,
} from '../../lib/api';
import AlertBadge from '../../components/AlertBadge';
import CriticalAlertModal, { type CriticalAlertData } from '../../components/CriticalAlertModal';

const { Title } = Typography;

export default function DoctorDashboard() {
  const nav = useNavigate();
  const [patients, setPatients] = useState<PatientListResponse | null>(null);
  const [alerts, setAlerts] = useState<DoctorAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [criticalAlert, setCriticalAlert] = useState<CriticalAlertData | null>(null);
  const [criticalStats, setCriticalStats] = useState({ open_count: 0 });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll for critical alerts every 30 seconds
  useEffect(() => {
    async function fetchCriticalAlerts() {
      try {
        const result = await listCriticalAlerts({ status: 'detected', page_size: 5 });
        const items: CriticalAlertData[] = result?.items || [];
        // Show the oldest unacknowledged critical alert
        if (items.length > 0) {
          const unacked = items.filter(
            (a) => ['detected', 'notified_doctor'].includes(a.status),
          );
          if (unacked.length > 0) {
            setCriticalAlert(unacked[0]);
          }
        }
        const stats = await getCriticalAlertStats();
        setCriticalStats(stats);
      } catch {
        // Silently handle polling errors
      }
    }

    fetchCriticalAlerts();
    pollRef.current = setInterval(fetchCriticalAlerts, 30000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const handleAcknowledge = useCallback(async (alertId: string, resolution: string, notes?: string) => {
    await acknowledgeCriticalAlert(alertId, { resolution, notes });
    setCriticalAlert(null);
    // Refresh alerts list
    try {
      const alertData = await getAllAlerts({ page_size: 10 });
      setAlerts(alertData?.items || alertData?.alerts || []);
    } catch { /* ignore */ }
  }, []);

  const handleCloseModal = useCallback(() => {
    setCriticalAlert(null);
  }, []);

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
    <>
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
          <Col xs={24} sm={6}>
            <Card hoverable onClick={() => nav('/doctor/patients')}>
              <Statistic
                title="管理患者总数"
                value={totalPatients}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card hoverable onClick={() => nav('/doctor/alerts')}>
              <Statistic
                title="未读预警"
                value={unacknowledgedAlerts}
                prefix={<AlertOutlined />}
                valueStyle={{ color: unacknowledgedAlerts > 0 ? '#ff4d4f' : '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
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
          <Col xs={24} sm={6}>
            <Card hoverable onClick={() => nav('/doctor/alerts')}>
              <Statistic
                title="危急值待处理"
                value={criticalStats.open_count}
                prefix={<AlertOutlined />}
                valueStyle={{ color: criticalStats.open_count > 0 ? '#ff4d4f' : '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Critical alert status bar */}
        {criticalStats.open_count > 0 && (
          <Card
            size="small"
            style={{ marginBottom: 16, background: '#fff2f0', border: '1px solid #ffccc7' }}
          >
            <Row align="middle" justify="space-between">
              <Col>
                <WarningOutlined style={{ color: '#ff4d4f', fontSize: 16, marginRight: 8 }} />
                <span style={{ color: '#cf1322', fontWeight: 600 }}>
                  危急值闭环管理: {criticalStats.open_count} 条待处理 |
                  已确认 {criticalStats.acknowledged_count} |
                  已解决 {criticalStats.resolved_count} |
                  已升级 {criticalStats.escalated_count}
                </span>
              </Col>
              <Col>
                <Button size="small" danger onClick={() => nav('/doctor/alerts')}>
                  查看详情
                </Button>
              </Col>
            </Row>
          </Card>
        )}

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
      <CriticalAlertModal
        alert={criticalAlert}
        onAcknowledge={handleAcknowledge}
        onClose={handleCloseModal}
      />
    </>
  );
}
