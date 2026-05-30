import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Button, Input, Select, Tag, Descriptions, Typography, Space, Row, Col,
  message, Spin, Empty, Modal, Divider,
} from 'antd';
import {
  EditOutlined, CheckOutlined, ArrowLeftOutlined, FileTextOutlined,
  HistoryOutlined, RobotOutlined, LockOutlined,
} from '@ant-design/icons';
import { getPatientDetail, type PatientDetailData } from '../../lib/api';
import ReactMarkdown from 'react-markdown';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ── Types ────────────────────────────────────────────────────────────────

interface RecordVersion {
  version: number;
  content: Record<string, string>;
  markdown: string;
  edited_by: string;
  edited_at: string;
}

interface MedicalRecordData {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  content: Record<string, string>;
  markdown: string;
  status: string;
  version: number;
  versions: RecordVersion[];
  created_at: string;
  updated_at: string;
}

interface RecordListItem {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

// ── Section labels ────────────────────────────────────────────────────────

const SOAP_SECTIONS: Record<string, string> = {
  subjective: 'S — 主观资料 (Subjective)',
  objective: 'O — 客观资料 (Objective)',
  assessment: 'A — 评估 (Assessment)',
  plan: 'P — 计划 (Plan)',
};

const DISCHARGE_SECTIONS: Record<string, string> = {
  admission_summary: '入院情况',
  hospital_course: '住院经过',
  discharge_diagnosis: '出院诊断',
  discharge_orders: '出院医嘱',
  follow_up_plan: '随访计划',
};

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  reviewed: 'blue',
  finalized: 'green',
};

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  reviewed: '已审核',
  finalized: '已定稿',
};

// ── Component ─────────────────────────────────────────────────────────────

export default function RecordEditor() {
  const { id: patientId } = useParams<{ id: string }>();
  const nav = useNavigate();

  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [records, setRecords] = useState<RecordListItem[]>([]);
  const [activeRecord, setActiveRecord] = useState<MedicalRecordData | null>(null);
  const [patientData, setPatientData] = useState<PatientDetailData | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [viewVersion, setViewVersion] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // ── Fetch patient data ──────────────────────────────────────────────
  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    async function fetch() {
      setLoading(true);
      try {
        const detail = await getPatientDetail(patientId!);
        if (!cancelled) setPatientData(detail);
      } catch {
        if (!cancelled) message.error('获取患者数据失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [patientId]);

  // ── Fetch records list ──────────────────────────────────────────────
  const fetchRecords = useCallback(async () => {
    if (!patientId) return;
    try {
      const resp = await fetch(`/api/v1/doctor/patients/${patientId}/records`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setRecords(data.items || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`获取记录列表失败: ${msg}`);
    }
  }, [patientId]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  // ── Fetch active record detail ──────────────────────────────────────
  const loadRecord = useCallback(async (recordId: string) => {
    try {
      const resp = await fetch(`/api/v1/doctor/records/${recordId}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: MedicalRecordData = await resp.json();
      setActiveRecord(data);
      setViewVersion(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`获取记录详情失败: ${msg}`);
    }
  }, []);

  // ── Generate SOAP Record ────────────────────────────────────────────
  const generateRecord = async () => {
    if (!patientId || !patientData) return;
    setGenerating(true);
    try {
      const detail = patientData;
      const latestFpg = detail.glucose_records?.find((g) => g.measure_type === 'fasting')?.value_mmol_l;
      const latestPpg = detail.glucose_records?.find((g) => g.measure_type === 'postprandial')?.value_mmol_l;
      const latestReport = detail.lab_reports?.[0];

      const encounterData = {
        pre_consult_summary: null,
        lab_results: latestReport?.results || {},
        glucose_records: detail.glucose_records?.slice(-10) || [],
        diagnosis_info: {
          diabetes_type: detail.diabetes_type,
          hba1c_target: detail.hba1c_target,
        },
        medications: [],
      };

      const resp = await fetch(`/api/v1/doctor/patients/${patientId}/records/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ encounter_data: encounterData }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: MedicalRecordData = await resp.json();
      setActiveRecord(data);
      message.success('病历生成成功');
      fetchRecords();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`病历生成失败: ${msg}`);
    } finally {
      setGenerating(false);
    }
  };

  // ── Inline section editing ──────────────────────────────────────────
  const startEdit = (sectionKey: string) => {
    if (!activeRecord) return;
    setEditingSection(sectionKey);
    setEditText(activeRecord.content[sectionKey] || '');
  };

  const cancelEdit = () => {
    setEditingSection(null);
    setEditText('');
  };

  const saveSection = async () => {
    if (!activeRecord || !editingSection) return;
    const newContent = { ...activeRecord.content, [editingSection]: editText };
    setSaving(true);
    try {
      const resp = await fetch(`/api/v1/doctor/records/${activeRecord.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const updated: MedicalRecordData = await resp.json();
      setActiveRecord(updated);
      setEditingSection(null);
      setEditText('');
      message.success('段落已保存');
      fetchRecords();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`保存失败: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  // ── Finalize ────────────────────────────────────────────────────────
  const finalize = async () => {
    if (!activeRecord) return;
    Modal.confirm({
      title: '确认定稿',
      content: '定稿后病历不可再编辑。确定要定稿吗？',
      okText: '确定定稿',
      cancelText: '取消',
      onOk: async () => {
        try {
          const resp = await fetch(`/api/v1/doctor/records/${activeRecord.id}/finalize`, {
            method: 'POST',
          });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const result = await resp.json();
          setActiveRecord({ ...activeRecord, status: result.status, updated_at: result.updated_at });
          message.success('病历已定稿');
          fetchRecords();
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : '未知错误';
          message.error(`定稿失败: ${msg}`);
        }
      },
    });
  };

  // ── Determine sections based on record type ─────────────────────────
  const sectionLabels = activeRecord?.record_type === 'discharge' ? DISCHARGE_SECTIONS : SOAP_SECTIONS;

  // ── Version display logic ───────────────────────────────────────────
  const displayContent = viewVersion !== null && activeRecord
    ? activeRecord.versions.find((v) => v.version === viewVersion)?.content || activeRecord.content
    : activeRecord?.content || {};

  const isFinalized = activeRecord?.status === 'finalized';

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav(`/doctor/patients/${patientId}`)}
          style={{ marginRight: 16 }}
        >
          返回详情
        </Button>
        <Title level={3} style={{ margin: 0 }}>智能病历</Title>
      </Row>

      <Row gutter={24}>
        {/* Left column: Records list + editor */}
        <Col xs={24} lg={16}>
          {/* Records List */}
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span>病历列表</span>
              </Space>
            }
            extra={
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={generateRecord}
                loading={generating}
                disabled={!patientId || loading}
              >
                生成SOAP病历
              </Button>
            }
            style={{ marginBottom: 16 }}
          >
            {records.length === 0 && !loading ? (
              <Empty description='暂无病历记录，点击"生成SOAP病历"创建' />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {records.map((r) => (
                  <Card
                    key={r.id}
                    size="small"
                    hoverable
                    onClick={() => loadRecord(r.id)}
                    style={{
                      cursor: 'pointer',
                      borderColor: activeRecord?.id === r.id ? '#1890ff' : undefined,
                    }}
                  >
                    <Row justify="space-between" align="middle">
                      <Col>
                        <Space>
                          <Tag color="blue">{r.record_type.toUpperCase()}</Tag>
                          <Tag color={STATUS_COLOR[r.status]}>{STATUS_LABEL[r.status]}</Tag>
                          <Text type="secondary">v{r.version}</Text>
                        </Space>
                      </Col>
                      <Col>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(r.created_at).toLocaleString('zh-CN')}
                        </Text>
                      </Col>
                    </Row>
                    <Text type="secondary" style={{ fontSize: 11 }}>ID: {r.id.slice(0, 8)}...</Text>
                  </Card>
                ))}
              </div>
            )}
          </Card>

          {/* Editor */}
          {activeRecord && (
            <Card
              title={
                <Space>
                  <span>病历编辑</span>
                  <Tag color={STATUS_COLOR[activeRecord.status]}>
                    {STATUS_LABEL[activeRecord.status]}
                  </Tag>
                  <Tag>v{activeRecord.version}</Tag>
                  {viewVersion !== null && (
                    <Tag color="orange">查看历史版本 v{viewVersion}</Tag>
                  )}
                </Space>
              }
              extra={
                <Space>
                  {/* Version history */}
                  {activeRecord.versions.length > 0 && (
                    <Select
                      placeholder="历史版本"
                      style={{ width: 140 }}
                      size="small"
                      value={viewVersion}
                      onChange={(v) => setViewVersion(v)}
                      allowClear
                      onClear={() => setViewVersion(null)}
                      options={[
                        { label: `v${activeRecord.version} (当前)`, value: null as unknown as number },
                        ...activeRecord.versions.map((v) => ({
                          label: `v${v.version} — ${new Date(v.edited_at).toLocaleDateString('zh-CN')}`,
                          value: v.version,
                        })),
                      ]}
                    />
                  )}
                  {!isFinalized && (
                    <Button
                      icon={<LockOutlined />}
                      onClick={finalize}
                      disabled={viewVersion !== null}
                    >
                      定稿
                    </Button>
                  )}
                </Space>
              }
            >
              {Object.entries(sectionLabels).map(([key, label]) => (
                <div key={key} style={{ marginBottom: 16 }}>
                  <Row justify="space-between" align="middle" style={{ marginBottom: 4 }}>
                    <Text strong>{label}</Text>
                    {!isFinalized && viewVersion === null && (
                      <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => startEdit(key)}
                        disabled={editingSection !== null}
                      >
                        编辑
                      </Button>
                    )}
                  </Row>
                  {editingSection === key ? (
                    <div>
                      <TextArea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={6}
                        autoFocus
                        style={{ marginBottom: 8 }}
                      />
                      <Space>
                        <Button
                          type="primary"
                          size="small"
                          icon={<CheckOutlined />}
                          onClick={saveSection}
                          loading={saving}
                        >
                          保存
                        </Button>
                        <Button size="small" onClick={cancelEdit} disabled={saving}>
                          取消
                        </Button>
                      </Space>
                    </div>
                  ) : (
                    <Paragraph
                      style={{
                        padding: '8px 12px',
                        background: '#fafafa',
                        borderRadius: 4,
                        border: '1px solid #f0f0f0',
                        whiteSpace: 'pre-wrap',
                        minHeight: 40,
                      }}
                    >
                      {displayContent[key] || '(空)'}
                    </Paragraph>
                  )}
                </div>
              ))}
            </Card>
          )}

          {!activeRecord && !loading && (
            <Card>
              <Empty description="请选择或生成一份病历" />
            </Card>
          )}

          {loading && (
            <div style={{ padding: 48, textAlign: 'center' }}>
              <Spin tip="加载中..." />
            </div>
          )}
        </Col>

        {/* Right column: Markdown preview */}
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span>预览</span>
              </Space>
            }
            style={{ position: 'sticky', top: 24 }}
          >
            {activeRecord?.markdown ? (
              <div
                className="markdown-preview"
                style={{
                  maxHeight: 'calc(100vh - 200px)',
                  overflow: 'auto',
                  fontSize: 14,
                  lineHeight: 1.8,
                }}
              >
                <ReactMarkdown>
                  {viewVersion !== null
                    ? activeRecord.versions.find((v) => v.version === viewVersion)?.markdown || activeRecord.markdown
                    : activeRecord.markdown
                  }
                </ReactMarkdown>
              </div>
            ) : (
              <Empty description="暂无内容预览" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
