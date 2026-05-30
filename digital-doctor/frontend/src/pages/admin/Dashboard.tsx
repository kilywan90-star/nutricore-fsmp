import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Spin, Empty } from 'antd';
import {
  TeamOutlined,
  UserOutlined,
  ClusterOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import { getDashboardStats, type DashboardStats } from '../../lib/api';

export default function AdminDashboard() {
  const nav = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        const data = await getDashboardStats();
        if (!cancelled) setStats(data);
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

  if (error || !stats) {
    return <Empty description={error || '无法加载数据'} />;
  }

  const unacknowledgedAlerts =
    (stats.alerts_by_severity?.critical || 0) +
    (stats.alerts_by_severity?.warning || 0) +
    (stats.alerts_by_severity?.info || 0);

  // Simple SVG pie for alerts by severity
  const totalAlerts = unacknowledgedAlerts || 1;
  const alertSegments = [
    { label: '危急', value: stats.alerts_by_severity?.critical || 0, color: '#ff4d4f' },
    { label: '预警', value: stats.alerts_by_severity?.warning || 0, color: '#faad14' },
    { label: '信息', value: stats.alerts_by_severity?.info || 0, color: '#1677ff' },
  ];

  // Simple gauge for glucose control rate
  const gaugeAngle = (stats.glucose_control_rate / 100) * 180;
  const gaugeColor =
    stats.glucose_control_rate >= 70 ? '#52c41a' :
    stats.glucose_control_rate >= 40 ? '#faad14' : '#ff4d4f';

  // Registration trend bar chart (simple CSS bars)
  const maxTrendCount = Math.max(...stats.patient_registration_trend.map((d) => d.count), 1);

  return (
    <div>
      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="患者总数"
              value={stats.total_patients}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="活跃患者(近30天)"
              value={stats.active_patients}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="医生数"
              value={stats.total_doctors}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="科室数"
              value={stats.total_departments}
              prefix={<ClusterOutlined />}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable onClick={() => nav('/admin/audit')}>
            <Statistic
              title="未确认预警"
              value={unacknowledgedAlerts}
              prefix={<AlertOutlined />}
              valueStyle={{ color: unacknowledgedAlerts > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="血糖达标率"
              value={stats.glucose_control_rate}
              prefix={<CheckCircleOutlined />}
              suffix="%"
              valueStyle={{ color: gaugeColor }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]}>
        {/* Patient Registration Trend (7 days) */}
        <Col xs={24} lg={12}>
          <Card title="近7日新增患者" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', height: 180, gap: 12, padding: '8px 0' }}>
              {stats.patient_registration_trend.map((day, i) => (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#1677ff', marginBottom: 4 }}>
                    {day.count}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: 40,
                      height: Math.max((day.count / maxTrendCount) * 120, 4),
                      background: '#1677ff',
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.3s',
                    }}
                  />
                  <span style={{ fontSize: 10, color: '#999', marginTop: 4 }}>
                    {day.date.slice(5)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* Alerts by Severity Pie */}
        <Col xs={24} lg={12}>
          <Card title="预警分布" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: 16 }}>
              <svg width="140" height="140" viewBox="0 0 140 140">
                {totalAlerts > 0 ? (
                  (() => {
                    let cumulativeAngle = 0;
                    return alertSegments
                      .filter((seg) => seg.value > 0)
                      .map((seg, i) => {
                        const sliceAngle = (seg.value / totalAlerts) * 360;
                        const startAngle = cumulativeAngle;
                        cumulativeAngle += sliceAngle;
                        const endAngle = cumulativeAngle;
                        const r = 60;
                        const cx = 70, cy = 70;
                        const x1 = cx + r * Math.cos((startAngle - 90) * Math.PI / 180);
                        const y1 = cy + r * Math.sin((startAngle - 90) * Math.PI / 180);
                        const x2 = cx + r * Math.cos((endAngle - 90) * Math.PI / 180);
                        const y2 = cy + r * Math.sin((endAngle - 90) * Math.PI / 180);
                        const large = sliceAngle > 180 ? 1 : 0;
                        return (
                          <path
                            key={i}
                            d={`M${cx} ${cy} L${x1} ${y1} A${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
                            fill={seg.color}
                          />
                        );
                      });
                  })()
                ) : (
                  <circle cx="70" cy="70" r="60" fill="#f0f0f0" />
                )}
              </svg>
              <div>
                {alertSegments.map((seg, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ width: 12, height: 12, borderRadius: 2, background: seg.color, display: 'inline-block' }} />
                    <span>{seg.label}: {seg.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Glucose control gauge */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="血糖控制率">
            <div style={{ textAlign: 'center', padding: 16 }}>
              <svg width="200" height="120" viewBox="0 0 200 120">
                {/* Background arc */}
                <path
                  d="M 20 110 A 90 90 0 0 1 180 110"
                  fill="none"
                  stroke="#f0f0f0"
                  strokeWidth="16"
                  strokeLinecap="round"
                />
                {/* Value arc */}
                <path
                  d={`M 20 110 A 90 90 0 ${gaugeAngle > 90 ? 1 : 0} 1 ${20 + 160 * (1 - Math.cos((gaugeAngle) * Math.PI / 180))} ${110 - 90 * Math.sin(gaugeAngle * Math.PI / 180)}`}
                  fill="none"
                  stroke={gaugeColor}
                  strokeWidth="16"
                  strokeLinecap="round"
                />
                {/* Pointer */}
                <line
                  x1="100"
                  y1="110"
                  x2={100 - 70 * Math.cos(gaugeAngle * Math.PI / 180)}
                  y2={110 - 70 * Math.sin(gaugeAngle * Math.PI / 180)}
                  stroke="#333"
                  strokeWidth="2"
                />
                <circle cx="100" cy="110" r="5" fill="#333" />
                <text x="100" y="65" textAnchor="middle" fontSize="28" fontWeight="bold" fill={gaugeColor}>
                  {stats.glucose_control_rate}%
                </text>
                <text x="25" y="105" textAnchor="middle" fontSize="10" fill="#999">0%</text>
                <text x="175" y="105" textAnchor="middle" fontSize="10" fill="#999">100%</text>
              </svg>
            </div>
          </Card>
        </Col>

        {/* Quick Actions */}
        <Col xs={24} lg={12}>
          <Card title="快捷操作">
            <Row gutter={[12, 12]}>
              <Col span={12}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => nav('/admin/departments')}
                  style={{ textAlign: 'center' }}
                >
                  <ClusterOutlined style={{ fontSize: 24, color: '#1677ff' }} />
                  <div style={{ marginTop: 8 }}>管理科室</div>
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => nav('/admin/doctors')}
                  style={{ textAlign: 'center' }}
                >
                  <TeamOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                  <div style={{ marginTop: 8 }}>管理医生</div>
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => nav('/admin/config')}
                  style={{ textAlign: 'center' }}
                >
                  <SettingOutlined style={{ fontSize: 24, color: '#faad14' }} />
                  <div style={{ marginTop: 8 }}>参数配置</div>
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => nav('/admin/audit')}
                  style={{ textAlign: 'center' }}
                >
                  <AuditOutlined style={{ fontSize: 24, color: '#13c2c2' }} />
                  <div style={{ marginTop: 8 }}>操作日志</div>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
