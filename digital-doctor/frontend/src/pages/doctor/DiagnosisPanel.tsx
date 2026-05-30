import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Table, Descriptions, Tag, Button, Form, InputNumber, Row, Col,
  Typography, Space, message, Spin, Empty, Progress,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SendOutlined, CalculatorOutlined, MedicineBoxOutlined, ArrowLeftOutlined,
} from '@ant-design/icons';
import { getPatientDetail, type PatientDetailData } from '../../lib/api';

const { Title, Text, Paragraph } = Typography;

// ── Types ────────────────────────────────────────────────────────────────

interface DiagnosisResult {
  patient_id: string;
  doctor_id: string;
  diagnosis: {
    primary_diagnosis: {
      type: string;
      subtype: string | null;
      confidence: 'high' | 'medium' | 'low';
      guideline_ref: string;
    };
    differentials: Array<{
      condition: string;
      probability: string;
      supporting_evidence: string;
      ruling_out_needed: string;
    }>;
    recommended_tests: Array<{
      test: string;
      urgency: string;
      rationale: string;
    }>;
    narrative: string;
    overall_confidence: number;
    method: string;
  };
}

interface HomaResult {
  patient_id: string;
  homa_ir: {
    homa_ir: number | null;
    interpretation: string;
    reference_range: string;
    clinical_significance: string;
  };
  homa_beta: {
    homa_beta: number | null;
    interpretation: string;
    reference_range: string;
    clinical_significance: string;
  };
}

interface DifferentialItem {
  condition: string;
  probability: string;
  supporting_evidence: string;
  ruling_out_needed: string;
}

interface TestItem {
  test: string;
  urgency: string;
  rationale: string;
}

// ── Props ─────────────────────────────────────────────────────────────────

interface DiagnosisPanelProps {
  patientId?: string;
  patientData?: Record<string, unknown>;
}

// ── Helpers ───────────────────────────────────────────────────────────────

const confidenceColor: Record<string, string> = {
  high: 'green',
  medium: 'orange',
  low: 'red',
};

const probabilityToPercent: Record<string, number> = {
  '高': 85,
  '中': 60,
  '低': 35,
  '极低': 10,
};

const urgencyTag: Record<string, string> = {
  '紧急': 'red',
  '常规': 'blue',
  '建议': 'default',
};

function confidencePercent(c: string): number {
  switch (c) {
    case 'high': return 90;
    case 'medium': return 65;
    case 'low': return 35;
    default: return 50;
  }
}

// ── Component ─────────────────────────────────────────────────────────────

export default function DiagnosisPanel({ patientId: propPatientId, patientData: propPatientData }: DiagnosisPanelProps) {
  const { id: routePatientId } = useParams<{ id: string }>();
  const nav = useNavigate();
  const patientId = propPatientId || routePatientId || '';

  const [loading, setLoading] = useState(false);
  const [fetchingPatient, setFetchingPatient] = useState(false);
  const [patientData, setPatientData] = useState<Record<string, unknown> | undefined>(propPatientData);
  const [diagResult, setDiagResult] = useState<DiagnosisResult | null>(null);
  const [homaResult, setHomaResult] = useState<HomaResult | null>(null);
  const [homaLoading, setHomaLoading] = useState(false);
  const [homaForm] = Form.useForm();

  // Fetch patient data from API if not provided as prop
  useEffect(() => {
    if (propPatientData) {
      setPatientData(propPatientData);
      return;
    }
    if (!patientId) return;
    let cancelled = false;
    async function fetch() {
      setFetchingPatient(true);
      try {
        const detail: PatientDetailData = await getPatientDetail(patientId);
        if (!cancelled) {
          setPatientData(detail as unknown as Record<string, unknown>);
        }
      } catch {
        if (!cancelled) message.error('获取患者数据失败');
      } finally {
        if (!cancelled) setFetchingPatient(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [patientId, propPatientData]);

  const buildPatientDataForDiagnosis = (): Record<string, unknown> => {
    const pd = patientData || {};
    const detail = pd as unknown as PatientDetailData;
    // Build clinical data dict from patient detail
    const latestGlucose = detail.glucose_records?.find(() => true);
    const latestFpg = detail.glucose_records?.find((g) => g.measure_type === 'fasting')?.value_mmol_l;
    const latestPpg = detail.glucose_records?.find((g) => g.measure_type === 'postprandial')?.value_mmol_l;
    const latestReport = detail.lab_reports?.[0];

    return {
      fpg: latestFpg ?? latestGlucose?.value_mmol_l,
      ppg: latestPpg,
      hba1c: latestReport?.results?.hba1c,
      bmi: (pd as Record<string, unknown>).bmi,
      age: detail.birth_year ? new Date().getFullYear() - detail.birth_year : undefined,
      gender: detail.gender,
      birth_year: detail.birth_year,
      diabetes_type: detail.diabetes_type,
      tc: latestReport?.results?.tc,
      tg: latestReport?.results?.tg,
      ldl: latestReport?.results?.ldl,
      hdl: latestReport?.results?.hdl,
      egfr: latestReport?.results?.egfr,
      waist_circumference: (pd as Record<string, unknown>).waist_circumference,
      blood_pressure: (pd as Record<string, unknown>).blood_pressure,
      family_history: (pd as Record<string, unknown>).family_history,
      has_hypertension: (pd as Record<string, unknown>).has_hypertension,
      physical_activity: (pd as Record<string, unknown>).physical_activity,
    };
  };

  const runDiagnosis = async () => {
    const diagnosisData = buildPatientDataForDiagnosis();
    if (!diagnosisData || Object.keys(diagnosisData).length === 0) {
      message.warning('缺少患者数据');
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch(`/api/v1/doctor/patients/${patientId}/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_data: diagnosisData,
          pre_consult_summary: null,
          lab_results: null,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: DiagnosisResult = await resp.json();
      setDiagResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`诊断分析失败: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const runHoma = async (values: { fasting_insulin: number; fasting_glucose: number }) => {
    setHomaLoading(true);
    try {
      const resp = await fetch(`/api/v1/doctor/patients/${patientId}/homa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: HomaResult = await resp.json();
      setHomaResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`HOMA计算失败: ${msg}`);
    } finally {
      setHomaLoading(false);
    }
  };

  const diffColumns: ColumnsType<DifferentialItem> = [
    {
      title: '鉴别诊断',
      dataIndex: 'condition',
      key: 'condition',
      width: 180,
    },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'probability',
      width: 160,
      render: (p: string) => (
        <Space>
          <Progress
            percent={probabilityToPercent[p] || 50}
            size="small"
            style={{ width: 80 }}
            showInfo={false}
            strokeColor={p === '高' ? '#52c41a' : p === '中' ? '#faad14' : '#ff4d4f'}
          />
          <Text>{p}</Text>
        </Space>
      ),
    },
    {
      title: '支持证据',
      dataIndex: 'supporting_evidence',
      key: 'evidence',
      ellipsis: true,
    },
    {
      title: '需排除',
      dataIndex: 'ruling_out_needed',
      key: 'ruling_out',
      width: 80,
      render: (v: string) => (
        <Tag color={v === '是' ? 'orange' : 'green'}>{v}</Tag>
      ),
    },
  ];

  const testColumns: ColumnsType<TestItem> = [
    {
      title: '推荐检查',
      dataIndex: 'test',
      key: 'test',
      width: 220,
    },
    {
      title: '紧急程度',
      dataIndex: 'urgency',
      key: 'urgency',
      width: 100,
      render: (u: string) => (
        <Tag color={urgencyTag[u] || 'default'}>{u}</Tag>
      ),
    },
    {
      title: '推荐理由',
      dataIndex: 'rationale',
      key: 'rationale',
      ellipsis: true,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav(`/doctor/patients/${patientId}`)}
          style={{ marginRight: 16 }}
        >
          返回详情
        </Button>
        <Title level={3} style={{ margin: 0 }}>辅助诊断</Title>
      </Row>

      {/* Primary Diagnosis Card */}
      <Card
        title={
          <Space>
            <MedicineBoxOutlined />
            <span>辅助诊断分析</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            onClick={runDiagnosis}
            loading={loading}
            disabled={!patientId || fetchingPatient}
          >
            开始分析
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        {!diagResult && !loading && !fetchingPatient && (
          <Empty description='点击"开始分析"启动辅助诊断' />
        )}

        {(loading || fetchingPatient) && (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <Spin tip="正在进行诊断分析..." />
          </div>
        )}

        {diagResult && (
          <>
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
                  <Descriptions.Item label="主诊断">
                    <Text strong style={{ fontSize: 16 }}>
                      {diagResult.diagnosis.primary_diagnosis.type}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="亚型">
                    {diagResult.diagnosis.primary_diagnosis.subtype || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="置信度">
                    <Progress
                      percent={confidencePercent(diagResult.diagnosis.primary_diagnosis.confidence)}
                      size="small"
                      style={{ width: 120 }}
                      strokeColor={confidenceColor[diagResult.diagnosis.primary_diagnosis.confidence]}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="综合置信度">
                    <Progress
                      percent={Math.round((diagResult.diagnosis.overall_confidence || 0) * 100)}
                      size="small"
                      style={{ width: 120 }}
                      format={(p) => `${p}%`}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="方法" span={1}>
                    <Tag>
                      {diagResult.diagnosis.method === 'rule_plus_llm' ? '规则引擎+LLM' : '规则引擎'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="指南引用">
                    <Text code>{diagResult.diagnosis.primary_diagnosis.guideline_ref}</Text>
                  </Descriptions.Item>
                </Descriptions>
              </Col>
            </Row>

            {diagResult.diagnosis.narrative && (
              <Paragraph
                style={{
                  marginTop: 16,
                  padding: '8px 12px',
                  background: '#f6ffed',
                  borderRadius: 6,
                  border: '1px solid #b7eb8f',
                }}
              >
                {diagResult.diagnosis.narrative}
              </Paragraph>
            )}
          </>
        )}
      </Card>

      {/* Differential Diagnosis Table */}
      {diagResult && diagResult.diagnosis.differentials.length > 0 && (
        <Card title="鉴别诊断" style={{ marginBottom: 24 }}>
          <Table<DifferentialItem>
            columns={diffColumns}
            dataSource={diagResult.diagnosis.differentials}
            rowKey={(r) => r.condition}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* Recommended Tests Checklist */}
      {diagResult && diagResult.diagnosis.recommended_tests.length > 0 && (
        <Card title="推荐检查项目" style={{ marginBottom: 24 }}>
          <Table<TestItem>
            columns={testColumns}
            dataSource={diagResult.diagnosis.recommended_tests}
            rowKey={(r) => r.test}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* HOMA Calculator */}
      <Card
        title={
          <Space>
            <CalculatorOutlined />
            <span>HOMA 计算器</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Form
          form={homaForm}
          layout="inline"
          onFinish={runHoma}
          style={{ marginBottom: 16 }}
        >
          <Form.Item
            name="fasting_insulin"
            label="空腹胰岛素 (μIU/mL)"
            rules={[{ required: true, message: '请输入空腹胰岛素值' }]}
          >
            <InputNumber min={0.1} step={0.1} style={{ width: 140 }} placeholder="如 8.5" />
          </Form.Item>
          <Form.Item
            name="fasting_glucose"
            label="空腹血糖 (mmol/L)"
            rules={[{ required: true, message: '请输入空腹血糖值' }]}
          >
            <InputNumber min={0.1} step={0.1} style={{ width: 140 }} placeholder="如 5.4" />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={homaLoading}
              icon={<CalculatorOutlined />}
            >
              计算
            </Button>
          </Form.Item>
        </Form>

        {homaResult && (
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card
                size="small"
                title="HOMA-IR（胰岛素抵抗指数）"
                style={{ marginBottom: 16 }}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="HOMA-IR 值">
                    <Text strong style={{ fontSize: 18 }}>
                      {homaResult.homa_ir.homa_ir !== null ? homaResult.homa_ir.homa_ir : '—'}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="解读">
                    <Tag color={
                      homaResult.homa_ir.interpretation.includes('正常') ? 'green'
                      : homaResult.homa_ir.interpretation.includes('临界') ? 'orange'
                      : homaResult.homa_ir.interpretation.includes('轻度') ? 'gold'
                      : 'red'
                    }>
                      {homaResult.homa_ir.interpretation}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="参考范围">
                    <Text type="secondary">{homaResult.homa_ir.reference_range}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="临床意义">
                    {homaResult.homa_ir.clinical_significance}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                size="small"
                title="HOMA-β（β细胞功能）"
                style={{ marginBottom: 16 }}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="HOMA-β 值">
                    <Text strong style={{ fontSize: 18 }}>
                      {homaResult.homa_beta.homa_beta !== null ? `${homaResult.homa_beta.homa_beta}%` : '—'}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="解读">
                    <Tag color={
                      homaResult.homa_beta.interpretation.includes('正常') ? 'green'
                      : homaResult.homa_beta.interpretation.includes('轻度') ? 'gold'
                      : homaResult.homa_beta.interpretation.includes('中度') ? 'orange'
                      : 'red'
                    }>
                      {homaResult.homa_beta.interpretation}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="参考范围">
                    <Text type="secondary">{homaResult.homa_beta.reference_range}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="临床意义">
                    {homaResult.homa_beta.clinical_significance}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        )}

        {!homaResult && (
          <Empty description="输入空腹胰岛素和空腹血糖值，点击计算" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* Send to Medical Record button (placeholder for P3-4) */}
      {diagResult && (
        <Card style={{ textAlign: 'center' }}>
          <Button
            type="default"
            icon={<SendOutlined />}
            size="large"
            onClick={() => message.info('病历发送功能将在P3-4中实现')}
          >
            发送至病历
          </Button>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">此功能将在后续版本中开放</Text>
          </div>
        </Card>
      )}
    </div>
  );
}
