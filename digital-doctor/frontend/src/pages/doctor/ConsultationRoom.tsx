import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Typography, Button, Form, Input, Select,
  Tag, Table, Space, Modal, Descriptions, message, Spin, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, MessageOutlined, SendOutlined,
  FileTextOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import {
  createConsultation, listConsultations, getConsultation, completeConsultation,
  type ConsultationItem, type ConsultationListResponse,
} from '../../lib/api';

const { Title, Text } = Typography;
const { TextArea } = Input;

const statusLabels: Record<string, string> = {
  requested: '已请求', accepted: '已接受', in_progress: '进行中', completed: '已完成',
};
const statusColors: Record<string, string> = {
  requested: 'processing', accepted: 'blue', in_progress: 'orange', completed: 'green',
};

export default function ConsultationRoom() {
  const nav = useNavigate();
  const [tab, setTab] = useState<'request' | 'list'>('request');
  const [loading, setLoading] = useState(false);

  // Request form
  const [form] = Form.useForm();

  // Consultation list
  const [consultList, setConsultList] = useState<ConsultationListResponse | null>(null);

  // Detail modal
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detail, setDetail] = useState<ConsultationItem | null>(null);
  const [completeForm] = Form.useForm();

  const fetchConsultations = async () => {
    try {
      const result = await listConsultations({ page_size: 50 });
      setConsultList(result);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchConsultations();
  }, []);

  const handleRequestConsultation = async () => {
    setLoading(true);
    try {
      const values = await form.validateFields();
      await createConsultation(values);
      message.success('远程会诊请求已发送');
      form.resetFields();
      fetchConsultations();
    } catch (err: any) {
      if (err?.message) message.error(err.message);
      else message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (id: string) => {
    try {
      const result = await getConsultation(id);
      setDetail(result);
      setDetailModalOpen(true);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '加载失败');
    }
  };

  const handleComplete = async () => {
    if (!detail) return;
    setLoading(true);
    try {
      const values = await completeForm.validateFields();
      await completeConsultation(detail.id, values);
      message.success('会诊已完成');
      setDetailModalOpen(false);
      fetchConsultations();
    } catch (err: any) {
      if (err?.message) message.error(err.message);
      else message.error('完成失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, render: (v: string) => v.slice(0, 8) + '...' },
    { title: '患者ID', dataIndex: 'patient_id', key: 'patient_id', width: 100, render: (v: string) => v.slice(0, 8) + '...' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>,
    },
    { title: '临床问题', dataIndex: 'clinical_question', key: 'clinical_question', ellipsis: true },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_: unknown, record: ConsultationItem) => (
        <Space size="small">
          <Button size="small" icon={<FileTextOutlined />} onClick={() => handleViewDetail(record.id)}>
            查看
          </Button>
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
        <Title level={3} style={{ margin: 0 }}>医联体远程会诊</Title>
      </Row>

      {/* Tab */}
      <Card style={{ marginBottom: 24 }}>
        <Space size="large">
          <Button type={tab === 'request' ? 'primary' : 'default'} onClick={() => setTab('request')}>
            发起会诊
          </Button>
          <Button type={tab === 'list' ? 'primary' : 'default'} onClick={() => setTab('list')}>
            会诊记录
          </Button>
        </Space>
      </Card>

      {/* Request tab */}
      {tab === 'request' && (
        <Card title="发起远程会诊请求">
          <Form form={form} layout="vertical">
            <Form.Item
              name="patient_id"
              label="患者ID"
              rules={[{ required: true, message: '请输入患者ID' }]}
            >
              <Input placeholder="患者UUID" />
            </Form.Item>
            <Form.Item
              name="clinical_question"
              label="临床问题"
              rules={[{ required: true, message: '请描述临床问题' }]}
            >
              <TextArea rows={4} placeholder="请详细描述需要会诊的临床问题，例如：该患者HbA1c持续不达标，已使用二甲双胍+格列美脲+达格列净三联治疗，是否需要启用胰岛素？" />
            </Form.Item>
            <Row gutter={[24, 0]}>
              <Col xs={24} sm={12}>
                <Form.Item name="consulting_hospital_id" label="会诊医院（可选）">
                  <Input placeholder="目标医院UUID" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="consulting_doctor_id" label="会诊医生（可选）">
                  <Input placeholder="目标医生UUID" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item>
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={loading}
                onClick={handleRequestConsultation}
                size="large"
              >
                发起会诊请求
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* List tab */}
      {tab === 'list' && (
        <Card title="会诊记录">
          <Table
            dataSource={consultList?.items || []}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 20, total: consultList?.total || 0 }}
            size="small"
          />
        </Card>
      )}

      {/* Detail modal */}
      <Modal
        title="会诊详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={750}
      >
        {detail ? (
          <>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="状态">
                <Tag color={statusColors[detail.status]}>{statusLabels[detail.status]}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(detail.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="临床问题" span={2}>
                {detail.clinical_question}
              </Descriptions.Item>
            </Descriptions>

            {/* AI-prepared summary */}
            {detail.ai_prepared_summary && (
              <Card title="AI 准备的病例摘要" size="small" style={{ marginBottom: 24 }}>
                {!!(detail.ai_prepared_summary as Record<string, unknown>).suggested_differentials && (
                  <>
                    <Title level={5}>鉴别诊断建议</Title>
                    <ul>
                      {(detail.ai_prepared_summary as Record<string, string[]>).suggested_differentials?.map((d: string, i: number) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </>
                )}
                {!!(detail.ai_prepared_summary as Record<string, unknown>).relevant_guidelines && (
                  <>
                    <Title level={5}>相关指南</Title>
                    <ul>
                      {(detail.ai_prepared_summary as Record<string, { title: string }[]>).relevant_guidelines?.map((g: { title: string }, i: number) => (
                        <li key={i}>{g.title}</li>
                      ))}
                    </ul>
                  </>
                )}
                {!!(detail.ai_prepared_summary as Record<string, unknown>).clinical_summary && (
                  <>
                    <Title level={5}>临床摘要</Title>
                    <pre style={{ fontSize: 11, maxHeight: 200, overflow: 'auto' }}>
                      {JSON.stringify(
                        (detail.ai_prepared_summary as Record<string, unknown>).clinical_summary,
                        null,
                        2,
                      )}
                    </pre>
                  </>
                )}
              </Card>
            )}

            {/* Existing notes/outcome */}
            {detail.consultation_notes && (
              <Card title="会诊记录" size="small" style={{ marginBottom: 24 }}>
                <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{detail.consultation_notes}</pre>
              </Card>
            )}
            {detail.outcome && (
              <Card title="会诊结论" size="small" style={{ marginBottom: 24 }}>
                <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{detail.outcome}</pre>
              </Card>
            )}

            {/* Complete form */}
            {detail.status !== 'completed' && (
              <Card title="完成会诊" size="small">
                <Form form={completeForm} layout="vertical">
                  <Form.Item name="notes" label="会诊记录">
                    <TextArea rows={4} placeholder="记录会诊讨论要点..." />
                  </Form.Item>
                  <Form.Item name="outcome" label="会诊结论">
                    <TextArea rows={3} placeholder="会诊结论和建议..." />
                  </Form.Item>
                  <Button
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    loading={loading}
                    onClick={handleComplete}
                  >
                    提交并完成会诊
                  </Button>
                </Form>
              </Card>
            )}
          </>
        ) : (
          <Spin />
        )}
      </Modal>
    </div>
  );
}
