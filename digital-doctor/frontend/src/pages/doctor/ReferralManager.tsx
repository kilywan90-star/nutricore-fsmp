import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Typography, Button, Form, Select, InputNumber,
  Switch, Tag, Table, Space, Modal, Descriptions, message, Spin, Empty, Input,
} from 'antd';
import {
  ArrowLeftOutlined, SendOutlined, SearchOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  evaluateReferral, searchReferralTargets, createReferral,
  listReferrals, acceptReferral, getReferralSummary,
  type ReferralEvaluation, type ReferralTarget,
  type ReferralItem, type ReferralListResponse,
} from '../../lib/api';

const { Title, Text } = Typography;

const urgencyLabels: Record<string, string> = { routine: '常规', urgent: '紧急', emergency: '危重' };
const urgencyColors: Record<string, string> = { routine: 'blue', urgent: 'orange', emergency: 'red' };
const levelLabels: Record<string, string> = { county: '县级', municipal: '市级', provincial: '省级' };
const statusLabels: Record<string, string> = {
  pending: '待接收', accepted: '已接收', rejected: '已拒绝', completed: '已完成',
};
const statusColors: Record<string, string> = {
  pending: 'processing', accepted: 'success', rejected: 'error', completed: 'default',
};

export default function ReferralManager() {
  const nav = useNavigate();
  const [tab, setTab] = useState<'evaluate' | 'sent' | 'received'>('evaluate');
  const [loading, setLoading] = useState(false);

  // Evaluation state
  const [evalForm] = Form.useForm();
  const [evaluation, setEvaluation] = useState<ReferralEvaluation | null>(null);
  const [targets, setTargets] = useState<ReferralTarget[]>([]);
  const [searchingTargets, setSearchingTargets] = useState(false);

  // Referral lists
  const [sentList, setSentList] = useState<ReferralListResponse | null>(null);
  const [receivedList, setReceivedList] = useState<ReferralListResponse | null>(null);

  // Modal
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [summaryData, setSummaryData] = useState<Record<string, unknown> | null>(null);

  const handleEvaluate = async () => {
    setLoading(true);
    try {
      const values = await evalForm.validateFields();
      const result = await evaluateReferral(values);
      setEvaluation(result);

      if (result.referral_needed) {
        const targetsResult = await searchReferralTargets({
          department: result.target_department,
          level: result.target_level,
        });
        setTargets(targetsResult);
      } else {
        setTargets([]);
      }
    } catch (err: any) {
      if (err?.message) message.error(err.message);
      else message.error('评估失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReferral = async (target: ReferralTarget, reason: string, urgency: string, targetDept: string, targetLevel: string) => {
    setLoading(true);
    try {
      await createReferral({
        patient_id: '00000000-0000-0000-0000-000000000001', // Temporary; real integration uses selected patient
        from_hospital_id: '00000000-0000-0000-0000-000000000001',
        to_hospital_id: target.id,
        urgency,
        target_department: targetDept,
        target_level: targetLevel,
        reason,
      });
      message.success('转诊申请已发送');
      setEvaluation(null);
      setTargets([]);
      evalForm.resetFields();
      fetchSentReferrals();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '创建转诊失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptReferral = async (referralId: string) => {
    try {
      await acceptReferral(referralId);
      message.success('已接收转诊');
      fetchReceivedReferrals();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '接收失败');
    }
  };

  const handleViewSummary = async (referralId: string) => {
    try {
      const result = await getReferralSummary(referralId);
      setSummaryData(result.clinical_summary);
      setSummaryModalOpen(true);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '加载失败');
    }
  };

  const fetchSentReferrals = async () => {
    try {
      const result = await listReferrals({ page_size: 50 });
      setSentList(result);
    } catch { /* silent */ }
  };

  const fetchReceivedReferrals = async () => {
    try {
      const result = await listReferrals({ status: 'pending', page_size: 50 });
      setReceivedList(result);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchSentReferrals();
    fetchReceivedReferrals();
  }, []);

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, render: (v: string) => v.slice(0, 8) + '...' },
    { title: '患者ID', dataIndex: 'patient_id', key: 'patient_id', width: 100, render: (v: string) => v.slice(0, 8) + '...' },
    { title: '目标科室', dataIndex: 'target_department', key: 'target_department', width: 100 },
    {
      title: '紧急程度', dataIndex: 'urgency', key: 'urgency', width: 80,
      render: (v: string) => <Tag color={urgencyColors[v] || 'default'}>{urgencyLabels[v] || v}</Tag>,
    },
    { title: '转诊原因', dataIndex: 'reason', key: 'reason', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 200,
      render: (_: unknown, record: ReferralItem) => (
        <Space size="small">
          <Button size="small" onClick={() => handleViewSummary(record.id)}>查看摘要</Button>
        </Space>
      ),
    },
  ];

  const receivedColumns = [
    ...columns.slice(0, 5),
    {
      title: '转出医院', dataIndex: 'from_hospital_name', key: 'from_hospital_name', width: 120,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 200,
      render: (_: unknown, record: ReferralItem) => (
        <Space size="small">
          <Button size="small" onClick={() => handleViewSummary(record.id)}>查看摘要</Button>
          {record.status === 'pending' && (
            <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => handleAcceptReferral(record.id)}>
              接收
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => nav('/doctor')} style={{ marginRight: 16 }}>
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>医联体转诊管理</Title>
      </Row>

      {/* Tab switcher */}
      <Card style={{ marginBottom: 24 }}>
        <Space size="large">
          <Button type={tab === 'evaluate' ? 'primary' : 'default'} onClick={() => setTab('evaluate')}>
            转诊评估
          </Button>
          <Button type={tab === 'sent' ? 'primary' : 'default'} onClick={() => setTab('sent')}>
            已发送转诊
          </Button>
          <Button type={tab === 'received' ? 'primary' : 'default'} onClick={() => setTab('received')}>
            待接收转诊
          </Button>
        </Space>
      </Card>

      {/* Evaluation tab */}
      {tab === 'evaluate' && (
        <>
          <Card title="转诊指征评估" style={{ marginBottom: 24 }}>
            <Form form={evalForm} layout="vertical">
              <Row gutter={[24, 0]}>
                <Col xs={24} sm={8}>
                  <Form.Item name="hba1c" label="HbA1c (%)">
                    <InputNumber style={{ width: '100%' }} min={4} max={20} step={0.1} placeholder="如 9.5" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="medication_count" label="降糖药物数" initialValue={0}>
                    <InputNumber style={{ width: '100%' }} min={0} max={10} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="egfr" label="eGFR (mL/min)">
                    <InputNumber style={{ width: '100%' }} min={1} max={200} placeholder="如 25" />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={[24, 0]}>
                <Col xs={24} sm={6}>
                  <Form.Item name="has_active_foot_ulcer" label="活动性足溃疡" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={6}>
                  <Form.Item name="recent_cvd_event" label="6月内CVD事件" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={6}>
                  <Form.Item name="severe_hypoglycemia_episodes" label="严重低血糖次数" initialValue={0}>
                    <InputNumber style={{ width: '100%' }} min={0} max={50} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={6}>
                  <Form.Item name="is_pregnant" label="妊娠合并糖尿病" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item>
                <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleEvaluate}>
                  评估转诊指征
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {evaluation && (
            <Card
              title="评估结果"
              style={{ marginBottom: 24, borderColor: evaluation.referral_needed ? '#faad14' : '#52c41a' }}
            >
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="是否需要转诊">
                  <Tag color={evaluation.referral_needed ? 'orange' : 'green'}>
                    {evaluation.referral_needed ? '建议转诊' : '暂无需转诊'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="紧急程度">
                  <Tag color={urgencyColors[evaluation.urgency]}>{urgencyLabels[evaluation.urgency]}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="目标科室">{evaluation.target_department}</Descriptions.Item>
                <Descriptions.Item label="目标级别">{levelLabels[evaluation.target_level]}</Descriptions.Item>
                <Descriptions.Item label="满足指征数">{evaluation.criteria_met}</Descriptions.Item>
                <Descriptions.Item label="转诊原因" span={2}>{evaluation.reason}</Descriptions.Item>
              </Descriptions>

              {evaluation.referral_needed && targets.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Title level={5}>可选转诊目标医院</Title>
                  <Row gutter={[16, 16]}>
                    {targets.map((t) => (
                      <Col xs={24} sm={12} key={t.id}>
                        <Card
                          size="small"
                          hoverable
                          actions={[
                            <Button
                              type="primary"
                              icon={<SendOutlined />}
                              onClick={() =>
                                handleCreateReferral(t, evaluation.reason, evaluation.urgency, evaluation.target_department, evaluation.target_level)
                              }
                            >
                              发送转诊
                            </Button>,
                          ]}
                        >
                          <Card.Meta
                            title={t.name}
                            description={
                              <>
                                <Text type="secondary">{t.level} | {t.department_name}</Text>
                                <br />
                                <Text type="secondary">{t.address}</Text>
                                <br />
                                <Text type="secondary">可用医生: {t.doctor_count}人</Text>
                              </>
                            }
                          />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </div>
              )}

              {evaluation.referral_needed && targets.length === 0 && (
                <Empty description="未找到符合条件的转诊目标医院" style={{ marginTop: 16 }} />
              )}
            </Card>
          )}
        </>
      )}

      {/* Sent referrals tab */}
      {tab === 'sent' && (
        <Card title="已发送转诊">
          <Table
            dataSource={sentList?.items || []}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 20, total: sentList?.total || 0 }}
            size="small"
          />
        </Card>
      )}

      {/* Received referrals tab */}
      {tab === 'received' && (
        <Card
          title={
            <Space>
              <span>待接收转诊</span>
              {receivedList && receivedList.total > 0 && (
                <Tag color="red">{receivedList.total}条待处理</Tag>
              )}
            </Space>
          }
        >
          <Table
            dataSource={receivedList?.items || []}
            columns={receivedColumns}
            rowKey="id"
            pagination={{ pageSize: 20, total: receivedList?.total || 0 }}
            size="small"
          />
        </Card>
      )}

      {/* Clinical summary modal */}
      <Modal
        title="临床摘要"
        open={summaryModalOpen}
        onCancel={() => setSummaryModalOpen(false)}
        footer={null}
        width={700}
      >
        {summaryData ? (
          <Descriptions column={1} bordered size="small">
            {!!summaryData.patient_demographics && (
              <Descriptions.Item label="患者信息">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(summaryData.patient_demographics, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            {!!summaryData.glucose_control_summary && (
              <Descriptions.Item label="血糖控制">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(summaryData.glucose_control_summary, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            {!!summaryData.current_medications && (
              <Descriptions.Item label="当前用药">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(summaryData.current_medications, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            {!!summaryData.complication_status && (
              <Descriptions.Item label="并发症状态">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(summaryData.complication_status, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        ) : (
          <Spin />
        )}
      </Modal>
    </div>
  );
}
