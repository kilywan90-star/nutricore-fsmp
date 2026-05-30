import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Button, Select, InputNumber, Input, Space, Tag, Spin, Empty,
  Typography, Collapse, Alert, Divider, Table, Badge, Descriptions, message,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, SearchOutlined, SafetyCertificateOutlined,
  WarningOutlined, CloseCircleOutlined, CheckCircleOutlined, ArrowLeftOutlined,
  ExperimentOutlined, ThunderboltOutlined, BulbOutlined,
} from '@ant-design/icons';
import {
  searchDrugs,
  reviewPrescription,
  checkDrugInteractions,
  type DrugInfo,
  type PrescriptionReviewIssue,
  type DrugInteractionResult,
} from '../../lib/api';
import ExplainabilityPanel from '../../components/ExplainabilityPanel';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface PrescriptionItem {
  key: string;
  drugName: string;
  dose: string;
  frequency: string;
  unit: string;
}

const FREQ_OPTIONS = [
  { label: 'qd (每日1次)', value: 'qd' },
  { label: 'bid (每日2次)', value: 'bid' },
  { label: 'tid (每日3次)', value: 'tid' },
  { label: 'qid (每日4次)', value: 'qid' },
  { label: 'qw (每周1次)', value: 'qw' },
  { label: 'qn (睡前)', value: 'qn' },
  { label: 'prn (按需)', value: 'prn' },
];

const SEVERITY_COLOR: Record<string, string> = {
  minor: 'blue',
  moderate: 'orange',
  major: 'red',
  contraindicated: '#ff0000',
};

const SEVERITY_LABEL: Record<string, string> = {
  minor: '轻微',
  moderate: '注意',
  major: '严重',
  contraindicated: '禁忌',
};

const RATING_CONFIG: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  safe: { color: '#52c41a', icon: <CheckCircleOutlined />, text: '安全' },
  caution: { color: '#faad14', icon: <WarningOutlined />, text: '需注意' },
  unsafe: { color: '#ff4d4f', icon: <CloseCircleOutlined />, text: '不安全' },
};

export default function PrescriptionReview() {
  const nav = useNavigate();

  // Diagnosis
  const [diagnosis, setDiagnosis] = useState('type2_diabetes');

  // Patient data
  const [patientConditions, setPatientConditions] = useState('');
  const [egfr, setEgfr] = useState<number | undefined>(80);
  const [alt, setAlt] = useState<number | undefined>(25);
  const [hba1c, setHba1c] = useState<number | undefined>(7.2);

  // Drug search
  const [searchOptions, setSearchOptions] = useState<DrugInfo[]>([]);
  const [searching, setSearching] = useState(false);

  // Prescription list
  const [prescription, setPrescription] = useState<PrescriptionItem[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<string | undefined>();
  const [doseInput, setDoseInput] = useState('500');
  const [unitInput, setUnitInput] = useState('mg');
  const [freqInput, setFreqInput] = useState('bid');

  // Review result
  const [reviewing, setReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState<{
    overall_rating: string;
    issues: PrescriptionReviewIssue[];
    summary: string;
    medication_count: number;
    issue_count: number;
  } | null>(null);

  // Interaction preview
  const [interactions, setInteractions] = useState<DrugInteractionResult[]>([]);

  // Explainability panel
  const [showExplainability, setShowExplainability] = useState(false);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [explanationData, setExplanationData] = useState<Record<string, unknown> | null>(null);

  // ── Drug search with debounce ──────────────────────────────────────────
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();

  const handleSearch = useCallback((query: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!query || query.length < 1) {
      setSearchOptions([]);
      return;
    }
    setSearching(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await searchDrugs(query);
        setSearchOptions(res.items || []);
      } catch {
        setSearchOptions([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  }, []);

  // ── Add drug to prescription ──────────────────────────────────────────
  const addDrug = () => {
    if (!selectedDrug) {
      message.warning('请选择药品');
      return;
    }
    const item: PrescriptionItem = {
      key: `${Date.now()}`,
      drugName: selectedDrug,
      dose: doseInput,
      unit: unitInput,
      frequency: freqInput,
    };
    const updated = [...prescription, item];
    setPrescription(updated);
    setSelectedDrug(undefined);
    setSearchOptions([]);

    // Auto-check interactions
    if (updated.length >= 2) {
      checkDrugInteractions(
        updated.map((p) => ({ drug_name: p.drugName })),
      ).then((res) => setInteractions(res.interactions || [])).catch(() => {});
    }
  };

  const removeDrug = (key: string) => {
    const updated = prescription.filter((p) => p.key !== key);
    setPrescription(updated);
    if (updated.length < 2) setInteractions([]);
  };

  // ── Review handler ─────────────────────────────────────────────────────
  const handleReview = async () => {
    if (prescription.length === 0) {
      message.warning('请先添加至少一种药品');
      return;
    }
    setReviewing(true);
    try {
      const patient_data: Record<string, unknown> = {
        conditions: patientConditions.split(',').map((s) => s.trim()).filter(Boolean),
      };
      const lab_results: Record<string, unknown> = {};
      if (egfr !== undefined) lab_results.egfr = egfr;
      if (alt !== undefined) lab_results.alt = alt;
      if (hba1c !== undefined) lab_results.hba1c = hba1c;

      const result = await reviewPrescription({
        diagnosis,
        medications: prescription.map((p) => ({
          name: p.drugName,
          dose: `${p.dose}${p.unit}`,
          frequency: p.frequency,
        })),
        patient_data,
        lab_results,
      });

      setReviewResult(result);
      setInteractions([]);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || '处方合理性检查失败');
    } finally {
      setReviewing(false);
    }
  };

  // ── Fetch explainability ──────────────────────────────────────────────
  const fetchExplainability = async () => {
    if (!reviewResult) return;
    setShowExplainability(true);
    setExplanationLoading(true);
    try {
      const patientConditionsList = patientConditions.split(',').map(s => s.trim()).filter(Boolean);
      const patientData = { conditions: patientConditionsList };
      const resp = await fetch('/api/v1/doctor/prescriptions/review/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_result: reviewResult,
          patient_data: patientData,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setExplanationData(data as Record<string, unknown>);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '未知错误';
      message.error(`获取审核依据失败: ${msg}`);
    } finally {
      setExplanationLoading(false);
    }
  };

  // ── Group issues by category ───────────────────────────────────────────
  const groupedIssues = (reviewResult?.issues || []).reduce<Record<string, PrescriptionReviewIssue[]>>((acc, iss) => {
    const cat = iss.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(iss);
    return acc;
  }, {});

  const ratingConf = reviewResult ? RATING_CONFIG[reviewResult.overall_rating] : null;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav('/doctor')}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>处方合理性提醒</Title>
      </Row>

      <Row gutter={[24, 24]}>
        {/* Left Column: Prescription Builder */}
        <Col xs={24} lg={12}>
          <Card title="患者信息" size="small" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Row gutter={12}>
                <Col span={12}>
                  <Text type="secondary">诊断类型</Text>
                  <Select
                    value={diagnosis}
                    onChange={setDiagnosis}
                    style={{ width: '100%' }}
                    options={[
                      { label: '2型糖尿病', value: 'type2_diabetes' },
                      { label: '新诊断2型糖尿病', value: 'type2_diabetes_newly_diagnosed' },
                    ]}
                  />
                </Col>
                <Col span={12}>
                  <Text type="secondary">合并症（逗号分隔）</Text>
                  <Input
                    placeholder="如: heart_failure, egfr<30, liver_disease"
                    value={patientConditions}
                    onChange={(e) => setPatientConditions(e.target.value)}
                  />
                </Col>
              </Row>
              <Row gutter={12}>
                <Col span={8}>
                  <Text type="secondary">eGFR (mL/min)</Text>
                  <InputNumber
                    min={0} max={200} style={{ width: '100%' }}
                    value={egfr} onChange={(v) => setEgfr(v ?? undefined)}
                  />
                </Col>
                <Col span={8}>
                  <Text type="secondary">ALT (U/L)</Text>
                  <InputNumber
                    min={0} max={2000} style={{ width: '100%' }}
                    value={alt} onChange={(v) => setAlt(v ?? undefined)}
                  />
                </Col>
                <Col span={8}>
                  <Text type="secondary">HbA1c (%)</Text>
                  <InputNumber
                    min={4} max={20} step={0.1} style={{ width: '100%' }}
                    value={hba1c} onChange={(v) => setHba1c(v ?? undefined)}
                  />
                </Col>
              </Row>
            </Space>
          </Card>

          <Card
            title="处方药品清单"
            size="small"
            style={{ marginBottom: 16 }}
            extra={
              <Text type="secondary">{prescription.length} 种药品</Text>
            }
          >
            {/* Drug Search + Add */}
            <Row gutter={8} style={{ marginBottom: 12 }}>
              <Col flex="auto">
                <Select
                  showSearch
                  value={selectedDrug}
                  placeholder="搜索药品（中文名/英文名/商品名）"
                  filterOption={false}
                  onSearch={handleSearch}
                  onChange={(val) => setSelectedDrug(val)}
                  onClear={() => { setSelectedDrug(undefined); setSearchOptions([]); }}
                  allowClear
                  notFoundContent={searching ? <Spin size="small" /> : <Empty description="未找到药品" />}
                  style={{ width: '100%' }}
                  options={searchOptions.map((d) => ({
                    label: `${d.generic_name} (${d.generic_name_en}) [${d.brand_names?.join(', ') || ''}]`,
                    value: d.generic_name_en,
                  }))}
                />
              </Col>
              <Col>
                <Input
                  placeholder="剂量"
                  value={doseInput}
                  onChange={(e) => setDoseInput(e.target.value)}
                  style={{ width: 80 }}
                />
              </Col>
              <Col>
                <Select
                  value={unitInput}
                  onChange={setUnitInput}
                  style={{ width: 70 }}
                  options={[
                    { label: 'mg', value: 'mg' },
                    { label: 'g', value: 'g' },
                    { label: 'mcg', value: 'mcg' },
                    { label: 'U', value: 'U' },
                  ]}
                />
              </Col>
              <Col>
                <Select
                  value={freqInput}
                  onChange={setFreqInput}
                  style={{ width: 130 }}
                  options={FREQ_OPTIONS}
                />
              </Col>
              <Col>
                <Button type="primary" icon={<PlusOutlined />} onClick={addDrug}>
                  添加
                </Button>
              </Col>
            </Row>

            {/* Prescription List */}
            {prescription.length === 0 ? (
              <Empty description="尚未添加药品" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table<PrescriptionItem>
                dataSource={prescription}
                rowKey="key"
                pagination={false}
                size="small"
                columns={[
                  { title: '药品', dataIndex: 'drugName', key: 'drugName' },
                  {
                    title: '剂量',
                    key: 'dose',
                    render: (_, r) => `${r.dose} ${r.unit}`,
                    width: 100,
                  },
                  {
                    title: '频次',
                    dataIndex: 'frequency',
                    key: 'frequency',
                    width: 100,
                    render: (f: string) => FREQ_OPTIONS.find((o) => o.value === f)?.label || f,
                  },
                  {
                    title: '',
                    key: 'action',
                    width: 40,
                    render: (_, r) => (
                      <Button
                        type="text" danger size="small" icon={<DeleteOutlined />}
                        onClick={() => removeDrug(r.key)}
                      />
                    ),
                  },
                ]}
              />
            )}
          </Card>

          <Button
            type="primary"
            size="large"
            block
            icon={<SafetyCertificateOutlined />}
            loading={reviewing}
            onClick={handleReview}
            disabled={prescription.length === 0}
          >
            合理性提醒
          </Button>

          {/* Live Interaction Preview */}
          {interactions.length > 0 && (
            <Card title="即时相互作用提示" size="small" style={{ marginTop: 12 }}>
              {interactions.map((ix, idx) => (
                <Alert
                  key={idx}
                  type={ix.severity === 'contraindicated' ? 'error' : ix.severity === 'major' ? 'warning' : 'info'}
                  message={`${ix.drug_a} + ${ix.drug_b}`}
                  description={ix.recommendation}
                  showIcon
                  style={{ marginBottom: 8 }}
                />
              ))}
            </Card>
          )}
        </Col>

        {/* Right Column: Review Results */}
        <Col xs={24} lg={12}>
          {reviewing ? (
            <div style={{ padding: 48, textAlign: 'center' }}>
              <Spin size="large" tip="正在进行处方合理性检查..." />
            </div>
          ) : reviewResult ? (
            <>
              {/* Overall Rating Badge */}
              <Card style={{ marginBottom: 16, textAlign: 'center' }}>
                <Space direction="vertical" size="small">
                  <div>
                    <Badge
                      count={ratingConf?.text}
                      style={{
                        backgroundColor: ratingConf?.color,
                        fontSize: 18,
                        padding: '8px 24px',
                        borderRadius: 4,
                        height: 'auto',
                      }}
                    />
                  </div>
                  <Text style={{ fontSize: 13, color: '#666' }}>{reviewResult.summary}</Text>
                  <Text type="secondary">
                    {reviewResult.medication_count} 种药品 | {reviewResult.issue_count} 条发现
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      * 本内容由AI生成，仅供临床参考，最终决策权归医生所有
                    </Text>
                  </div>
                  <Button
                    type="default"
                    icon={<BulbOutlined />}
                    onClick={fetchExplainability}
                    style={{ marginTop: 8 }}
                  >
                    查看审核依据
                  </Button>
                </Space>
              </Card>

              {/* Explainability Panel */}
              {showExplainability && (
                <Card title="处方审核依据" style={{ marginBottom: 16 }}>
                  <ExplainabilityPanel
                    type="prescription"
                    loading={explanationLoading}
                    prescriptionData={explanationData as Record<string, unknown>}
                  />
                </Card>
              )}

              {/* Issues by Category */}
              {Object.keys(groupedIssues).length === 0 ? (
                <Card>
                  <Empty description="未发现用药问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </Card>
              ) : (
                <Collapse defaultActiveKey={Object.keys(groupedIssues)}>
                  {/* Guideline Concordance */}
                  {groupedIssues.guideline_concordance && (
                    <Panel
                      header={
                        <Space>
                          <ExperimentOutlined />
                          <span>指南符合性 ({groupedIssues.guideline_concordance.length})</span>
                        </Space>
                      }
                      key="guideline_concordance"
                    >
                      {groupedIssues.guideline_concordance.map((iss, idx) => (
                        <Alert
                          key={idx}
                          type={iss.severity === 'contraindicated' ? 'error' : 'warning'}
                          message={iss.description}
                          description={
                            <>
                              <Paragraph style={{ marginBottom: 4 }}>{iss.recommendation}</Paragraph>
                              <Text type="secondary" style={{ fontSize: 12 }}>{iss.guideline_ref}</Text>
                            </>
                          }
                          showIcon
                          style={{ marginBottom: 8 }}
                        />
                      ))}
                    </Panel>
                  )}

                  {/* Drug Interactions */}
                  {groupedIssues.drug_interaction && (
                    <Panel
                      header={
                        <Space>
                          <ThunderboltOutlined />
                          <span>药物相互作用 ({groupedIssues.drug_interaction.length})</span>
                        </Space>
                      }
                      key="drug_interaction"
                    >
                      {groupedIssues.drug_interaction.map((iss, idx) => (
                        <Alert
                          key={idx}
                          type={iss.severity === 'contraindicated' ? 'error' : iss.severity === 'major' ? 'warning' : 'info'}
                          message={
                            <Space>
                              <Tag color={SEVERITY_COLOR[iss.severity]}>{SEVERITY_LABEL[iss.severity]}</Tag>
                              {iss.description}
                            </Space>
                          }
                          description={
                            <>
                              <Paragraph style={{ marginBottom: 4 }}>{iss.recommendation}</Paragraph>
                              <Text type="secondary" style={{ fontSize: 12 }}>{iss.guideline_ref}</Text>
                            </>
                          }
                          showIcon
                          style={{ marginBottom: 8 }}
                        />
                      ))}
                    </Panel>
                  )}

                  {/* Renal Dosing */}
                  {groupedIssues.renal_dosing && (
                    <Panel
                      header={
                        <Space>
                          <SearchOutlined />
                          <span>肾功能剂量调整 ({groupedIssues.renal_dosing.length})</span>
                        </Space>
                      }
                      key="renal_dosing"
                    >
                      {groupedIssues.renal_dosing.map((iss, idx) => (
                        <Alert
                          key={idx}
                          type={iss.severity === 'major' ? 'warning' : 'info'}
                          message={iss.description}
                          description={
                            <>
                              <Paragraph style={{ marginBottom: 4 }}>{iss.recommendation}</Paragraph>
                              <Text type="secondary" style={{ fontSize: 12 }}>{iss.guideline_ref}</Text>
                            </>
                          }
                          showIcon
                          style={{ marginBottom: 8 }}
                        />
                      ))}
                    </Panel>
                  )}

                  {/* Hepatic Dosing */}
                  {groupedIssues.hepatic_dosing && (
                    <Panel
                      header={
                        <Space>
                          <WarningOutlined />
                          <span>肝功能注意事项 ({groupedIssues.hepatic_dosing.length})</span>
                        </Space>
                      }
                      key="hepatic_dosing"
                    >
                      {groupedIssues.hepatic_dosing.map((iss, idx) => (
                        <Alert
                          key={idx}
                          type="error"
                          message={iss.description}
                          description={
                            <>
                              <Paragraph style={{ marginBottom: 4 }}>{iss.recommendation}</Paragraph>
                              <Text type="secondary" style={{ fontSize: 12 }}>{iss.guideline_ref}</Text>
                            </>
                          }
                          showIcon
                          style={{ marginBottom: 8 }}
                        />
                      ))}
                    </Panel>
                  )}

                  {/* Contraindications */}
                  {groupedIssues.contraindication && (
                    <Panel
                      header={
                        <Space>
                          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                          <span style={{ color: '#ff4d4f' }}>
                            禁忌症 ({groupedIssues.contraindication.length})
                          </span>
                        </Space>
                      }
                      key="contraindication"
                    >
                      {groupedIssues.contraindication.map((iss, idx) => (
                        <Alert
                          key={idx}
                          type="error"
                          message={iss.description}
                          description={
                            <>
                              <Paragraph style={{ marginBottom: 4 }}>{iss.recommendation}</Paragraph>
                              <Text type="secondary" style={{ fontSize: 12 }}>{iss.guideline_ref}</Text>
                            </>
                          }
                          showIcon
                          style={{ marginBottom: 8 }}
                        />
                      ))}
                    </Panel>
                  )}
                </Collapse>
              )}
            </>
          ) : (
            <Card>
              <Empty
                description="添加药品并点击「合理性提醒」查看结果"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
