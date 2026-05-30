import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Descriptions, Table, List, Typography, Button, Spin, Empty, Tag, Tabs,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  getPatientDetail,
  type PatientDetailData,
  type LabReportItem,
  type AlertItem,
} from '../../lib/api';
import GlucoseChart from '../../components/GlucoseChart';
import AlertBadge from '../../components/AlertBadge';
import CGMDashboard from '../../components/CGMDashboard';

const { Title } = Typography;

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [patient, setPatient] = useState<PatientDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function fetchDetail() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPatientDetail(id!);
        if (!cancelled) setPatient(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || '加载患者详情失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchDetail();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => nav('/doctor/patients')}>返回列表</Button>
        <Empty description={error} style={{ marginTop: 48 }} />
      </div>
    );
  }

  if (!patient) {
    return (
      <div style={{ padding: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => nav('/doctor/patients')}>返回列表</Button>
        <Empty description="患者不存在" style={{ marginTop: 48 }} />
      </div>
    );
  }

  const currentYear = dayjs().year();
  const age = currentYear - patient.birth_year;

  const labColumns: ColumnsType<LabReportItem> = [
    {
      title: '报告类型',
      dataIndex: 'report_type',
      key: 'report_type',
      width: 160,
      render: (t: string) => {
        const labels: Record<string, string> = {
          blood_glucose_panel: '血糖组套',
          hba1c_only: '糖化血红蛋白',
          lipid_panel: '血脂组套',
          renal_function: '肾功能',
        };
        return labels[t] || t;
      },
    },
    {
      title: '日期',
      dataIndex: 'report_date',
      key: 'report_date',
      width: 120,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD'),
    },
    {
      title: '检测结果',
      dataIndex: 'results',
      key: 'results',
      render: (results: Record<string, number>) =>
        Object.entries(results || {}).map(([k, v]) => (
          <Tag key={k} style={{ marginBottom: 4 }}>
            {k}: {v}
          </Tag>
        )),
    },
    {
      title: 'AI解读',
      dataIndex: 'ai_interpretation',
      key: 'ai_interpretation',
      ellipsis: true,
      render: (text: string) => text || <span style={{ color: '#999' }}>暂无解读</span>,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav('/doctor/patients')}
          style={{ marginRight: 16 }}
        >
          返回列表
        </Button>
        <Title level={3} style={{ margin: 0 }}>患者详情</Title>
      </Row>

      {/* Patient Info Card */}
      <Card title="基本信息" style={{ marginBottom: 24 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered size="small">
          <Descriptions.Item label="患者ID">{patient.id.slice(0, 8)}...</Descriptions.Item>
          <Descriptions.Item label="性别">{patient.gender === 'M' ? '男' : patient.gender === 'F' ? '女' : patient.gender}</Descriptions.Item>
          <Descriptions.Item label="年龄">{age} 岁（{patient.birth_year}年出生）</Descriptions.Item>
          <Descriptions.Item label="糖尿病类型">
            {patient.diabetes_type === 'type2' ? '2型糖尿病' : patient.diabetes_type === 'type1' ? '1型糖尿病' : patient.diabetes_type}
          </Descriptions.Item>
          <Descriptions.Item label="确诊日期">
            {patient.diagnosis_date ? dayjs(patient.diagnosis_date).format('YYYY-MM-DD') : '未知'}
          </Descriptions.Item>
          <Descriptions.Item label="HbA1c控制目标">
            <span style={{ color: '#1677ff', fontWeight: 600 }}>{patient.hba1c_target}%</span>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs
        defaultActiveKey="glucose"
        items={[
          {
            key: 'glucose',
            label: '血糖记录',
            children: (
              <div>
                <Card title="血糖趋势" style={{ marginBottom: 24 }}>
                  <div style={{ overflowX: 'auto' }}>
                    <GlucoseChart
                      data={(patient.glucose_records || []).map((g) => ({
                        value_mmol_l: g.value_mmol_l,
                        recorded_at: g.recorded_at,
                        measure_type: g.measure_type,
                      }))}
                    />
                  </div>
                  {patient.glucose_records && patient.glucose_records.length > 0 && (
                    <div style={{ marginTop: 8, display: 'flex', gap: 24, color: '#666', fontSize: 13 }}>
                      <span>记录数: {patient.glucose_records.length}</span>
                      <span>
                        平均值:{' '}
                        {(patient.glucose_records.reduce((s, g) => s + g.value_mmol_l, 0) / patient.glucose_records.length).toFixed(1)}{' '}
                        mmol/L
                      </span>
                    </div>
                  )}
                </Card>
              </div>
            ),
          },
          {
            key: 'cgm',
            label: '动态血糖 (CGM)',
            children: <CGMDashboard patientId={patient.id} />,
          },
          {
            key: 'lab',
            label: '化验报告',
            children: (
              <Card title="化验报告">
                <Table<LabReportItem>
                  columns={labColumns}
                  dataSource={patient.lab_reports || []}
                  rowKey="id"
                  pagination={{ pageSize: 5, showTotal: (t) => `共 ${t} 份报告` }}
                  locale={{ emptyText: '暂无化验报告' }}
                />
              </Card>
            ),
          },
          {
            key: 'alerts',
            label: '预警记录',
            children: (
              <Card title="预警记录">
                {!patient.alerts || patient.alerts.length === 0 ? (
                  <Empty description="暂无预警" />
                ) : (
                  <List
                    dataSource={patient.alerts}
                    renderItem={(item: AlertItem) => (
                      <List.Item
                        key={item.id}
                        extra={
                          <AlertBadge severity={item.severity as 'info' | 'warning' | 'critical'}>
                            {item.severity === 'critical' ? '危急' : item.severity === 'warning' ? '预警' : '信息'}
                          </AlertBadge>
                        }
                      >
                        <List.Item.Meta
                          title={
                            <span>
                              {item.title}
                              {item.acknowledged ? (
                                <Tag color="green" style={{ marginLeft: 8 }}>已确认</Tag>
                              ) : (
                                <Tag color="red" style={{ marginLeft: 8 }}>未确认</Tag>
                              )}
                            </span>
                          }
                          description={
                            <span>
                              {dayjs(item.created_at).format('YYYY-MM-DD HH:mm')} | {item.detail}
                            </span>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}

