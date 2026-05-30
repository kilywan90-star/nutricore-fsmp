import { useState } from 'react';
import {
  Card, Collapse, Typography, Progress, Tag, Space, Empty, Spin, Descriptions,
  Row, Col, Divider, Tooltip, Badge,
} from 'antd';
import {
  BulbOutlined, CheckCircleOutlined, CloseCircleOutlined,
  MinusCircleOutlined, SafetyCertificateOutlined, InfoCircleOutlined,
  ExperimentOutlined, ThunderboltOutlined, WarningOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// ── Types ────────────────────────────────────────────────────────────────

interface FactorContributionItem {
  factor: string;
  value: unknown;
  threshold: string;
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;
  guideline_ref: string;
}

interface ConfidenceBreakdown {
  rule_score: number;
  llm_score: number | null;
  combined: number;
}

interface DiagnosisExplanationData {
  primary_diagnosis: string;
  confidence: number;
  primary_factors: FactorContributionItem[];
  rule_contributions: Array<{
    rule_id: string;
    rule_name: string;
    matched: boolean;
    weight: number;
    guideline_ref: string;
  }>;
  differentials: Array<{
    condition: string;
    probability: string;
    supporting_evidence: string;
    ruling_out_needed: string;
    factor_contributions: Array<{
      factor: string;
      value: string;
      impact: string;
      guideline_ref: string;
    }>;
  }>;
  summary: string;
  confidence_breakdown?: ConfidenceBreakdown;
}

interface PrescriptionIssueExplanation {
  severity: string;
  category: string;
  description: string;
  recommendation: string;
  guideline_ref: string;
  contributing_factors: Array<{
    factor: string;
    value: string;
    impact: string;
    explanation: string;
  }>;
  recommendation_rationale: string;
}

interface PrescriptionExplanationData {
  overall_rating: string;
  issues: PrescriptionIssueExplanation[];
  summary: string;
}

interface RiskFactorItem {
  factor: string;
  factor_key: string;
  score: number;
  impact_pct: number;
  threshold: string;
  guideline_ref: string;
  actionable_advice?: string;
}

interface RiskExplanationData {
  risk_level: string;
  contributing_factors: RiskFactorItem[];
  modifiable_factors: RiskFactorItem[];
  summary: string;
}

// ── Props ─────────────────────────────────────────────────────────────────

interface ExplainabilityPanelProps {
  type: 'diagnosis' | 'prescription' | 'risk';
  loading?: boolean;
  // Diagnosis
  diagnosisData?: DiagnosisExplanationData;
  // Prescription
  prescriptionData?: PrescriptionExplanationData;
  // Risk
  riskData?: RiskExplanationData;
}

// ── Helpers ───────────────────────────────────────────────────────────────

const IMPACT_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  positive: { color: '#52c41a', icon: <CheckCircleOutlined />, label: '支持' },
  negative: { color: '#ff4d4f', icon: <CloseCircleOutlined />, label: '排除' },
  neutral: { color: '#8c8c8c', icon: <MinusCircleOutlined />, label: '参考' },
};

const SEVERITY_COLOR: Record<string, string> = {
  minor: 'blue',
  moderate: 'orange',
  major: 'red',
  contraindicated: '#ff0000',
};

const RATING_CONFIG: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  safe: { color: '#52c41a', icon: <CheckCircleOutlined />, text: '安全' },
  caution: { color: '#faad14', icon: <WarningOutlined />, text: '需注意' },
  unsafe: { color: '#ff4d4f', icon: <CloseCircleOutlined />, text: '不安全' },
};

// ── Factor Bar ────────────────────────────────────────────────────────────

function FactorBar({ factor }: { factor: FactorContributionItem }) {
  const config = IMPACT_CONFIG[factor.impact] || IMPACT_CONFIG.neutral;
  const pct = Math.round(factor.weight * 100);

  return (
    <div style={{ marginBottom: 12 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 2 }}>
        <Col>
          <Space size={4}>
            <Tooltip title={config.label}>
              <span style={{ color: config.color }}>{config.icon}</span>
            </Tooltip>
            <Text strong>{factor.factor}</Text>
          </Space>
        </Col>
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            权重 {pct}%
          </Text>
        </Col>
      </Row>
      <Progress
        percent={pct}
        size="small"
        showInfo={false}
        strokeColor={config.color}
        trailColor="#f0f0f0"
        style={{ marginBottom: 4 }}
      />
      <Row justify="space-between">
        <Col>
          <Tooltip title={factor.threshold}>
            <Text style={{ fontSize: 12, color: '#666' }}>
              实际值: {String(factor.value)}
            </Text>
          </Tooltip>
        </Col>
        <Col>
          <Tooltip title={factor.guideline_ref}>
            <Text code style={{ fontSize: 11 }}>
              {factor.guideline_ref.length > 40
                ? factor.guideline_ref.slice(0, 40) + '...'
                : factor.guideline_ref}
            </Text>
          </Tooltip>
        </Col>
      </Row>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────

export default function ExplainabilityPanel({
  type,
  loading = false,
  diagnosisData,
  prescriptionData,
  riskData,
}: ExplainabilityPanelProps) {

  if (loading) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Spin tip="正在生成分析依据..." />
      </div>
    );
  }

  // ── Diagnosis Panel ───────────────────────────────────────────────────
  if (type === 'diagnosis' && diagnosisData) {
    const posFactors = diagnosisData.primary_factors.filter(f => f.impact === 'positive');
    const negFactors = diagnosisData.primary_factors.filter(f => f.impact === 'negative');
    const neuFactors = diagnosisData.primary_factors.filter(f => f.impact === 'neutral');

    return (
      <div>
        {/* Summary */}
        <Card style={{ marginBottom: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space>
              <BulbOutlined style={{ color: '#52c41a' }} />
              <Text strong>诊断分析依据</Text>
            </Space>
            <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>
              {diagnosisData.summary}
            </Paragraph>
            <Text type="secondary" style={{ fontSize: 11 }}>
              * 本内容由AI生成，仅供临床参考，最终决策权归医生所有
            </Text>
          </Space>
        </Card>

        {/* Confidence */}
        <Card title="置信度评估" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col span={12} style={{ textAlign: 'center' }}>
              <Text type="secondary">综合置信度</Text>
              <Progress
                type="circle"
                percent={Math.round(diagnosisData.confidence * 100)}
                size={80}
                strokeColor={{
                  '0%': '#52c41a',
                  '100': '#ff4d4f',
                }}
              />
            </Col>
            <Col span={12}>
              {diagnosisData.rule_contributions.map((rc, idx) => (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <Row justify="space-between">
                    <Text strong={rc.matched} type={rc.matched ? undefined : 'secondary'}>
                      {rc.rule_name}
                    </Text>
                    <Tag color={rc.matched ? 'green' : 'default'}>
                      {rc.matched ? `权重 ${Math.round(rc.weight * 100)}%` : '未匹配'}
                    </Tag>
                  </Row>
                  {rc.guideline_ref && (
                    <Tooltip title={rc.guideline_ref}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {rc.guideline_ref.slice(0, 60)}
                      </Text>
                    </Tooltip>
                  )}
                </div>
              ))}
            </Col>
          </Row>
        </Card>

        {/* Primary Factors */}
        <Card title={`支持诊断的因素 (${posFactors.length})`} size="small" style={{ marginBottom: 12 }}>
          {posFactors.length === 0 ? (
            <Empty description="无明确支持因素" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            posFactors.map((f, i) => <FactorBar key={i} factor={f} />)
          )}
        </Card>

        <Collapse ghost style={{ marginBottom: 16 }}>
          {negFactors.length > 0 && (
            <Panel
              header={`排除诊断的因素 (${negFactors.length})`}
              key="negative"
            >
              {negFactors.map((f, i) => <FactorBar key={i} factor={f} />)}
            </Panel>
          )}
          {neuFactors.length > 0 && (
            <Panel
              header={`参考因素 (${neuFactors.length})`}
              key="neutral"
            >
              {neuFactors.map((f, i) => <FactorBar key={i} factor={f} />)}
            </Panel>
          )}
        </Collapse>

        {/* Differentials */}
        {diagnosisData.differentials.length > 0 && (
          <Collapse ghost>
            <Panel
              header={`鉴别诊断详情 (${diagnosisData.differentials.length})`}
              key="differentials"
            >
              {diagnosisData.differentials.map((diff, idx) => (
                <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Space>
                      <Text strong>{diff.condition}</Text>
                      <Tag color={diff.probability === '高' ? 'green' : diff.probability === '中' ? 'orange' : 'red'}>
                        概率: {diff.probability}
                      </Tag>
                      <Tag color={diff.ruling_out_needed === '是' ? 'orange' : 'green'}>
                        {diff.ruling_out_needed === '是' ? '需排除' : '可排除'}
                      </Tag>
                    </Space>
                    <Text>{diff.supporting_evidence}</Text>
                    {diff.factor_contributions.length > 0 && (
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>分析依据：</Text>
                        {diff.factor_contributions.map((fc, fidx) => (
                          <div key={fidx} style={{ paddingLeft: 12 }}>
                            <Text style={{ fontSize: 12 }}>
                              - {fc.factor}: {fc.value}
                              <Tooltip title={fc.guideline_ref}>
                                <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                              </Tooltip>
                            </Text>
                          </div>
                        ))}
                      </div>
                    )}
                  </Space>
                </Card>
              ))}
            </Panel>
          </Collapse>
        )}
      </div>
    );
  }

  // ── Prescription Panel ────────────────────────────────────────────────
  if (type === 'prescription' && prescriptionData) {
    const ratingConf = RATING_CONFIG[prescriptionData.overall_rating] || RATING_CONFIG.safe;

    return (
      <div>
        {/* Summary */}
        <Card style={{ marginBottom: 16, textAlign: 'center' }}>
          <Space direction="vertical" size="small">
            <Badge
              count={ratingConf.text}
              style={{
                backgroundColor: ratingConf.color,
                fontSize: 16,
                padding: '6px 20px',
                borderRadius: 4,
                height: 'auto',
              }}
            />
            <Text style={{ fontSize: 13, color: '#666' }}>{prescriptionData.summary}</Text>
          </Space>
        </Card>

        {/* Issues with factor attribution */}
        {prescriptionData.issues.map((issue, idx) => {
          const issueIcon =
            issue.severity === 'contraindicated' ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> :
            issue.severity === 'major' ? <WarningOutlined style={{ color: '#ff4d4f' }} /> :
            <InfoCircleOutlined style={{ color: '#faad14' }} />;

          return (
            <Card
              key={idx}
              size="small"
              style={{ marginBottom: 8 }}
              title={
                <Space>
                  {issueIcon}
                  <Tag color={SEVERITY_COLOR[issue.severity]}>
                    {issue.severity === 'contraindicated' ? '禁忌' :
                     issue.severity === 'major' ? '严重' :
                     issue.severity === 'moderate' ? '注意' : '轻微'}
                  </Tag>
                  <Text>{issue.category === 'guideline_concordance' ? '指南符合性' :
                         issue.category === 'drug_interaction' ? '药物相互作用' :
                         issue.category === 'renal_dosing' ? '肾功能剂量调整' :
                         issue.category === 'hepatic_dosing' ? '肝功能注意事项' :
                         issue.category === 'contraindication' ? '禁忌症' :
                         issue.category === 'allergy' ? '过敏交叉' :
                         issue.category === 'pregnancy_safety' ? '妊娠安全性' :
                         issue.category}</Text>
                </Space>
              }
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Text>{issue.description}</Text>

                {/* Contributing factors */}
                {issue.contributing_factors.length > 0 && (
                  <div style={{
                    background: '#fffbe6',
                    border: '1px solid #ffe58f',
                    borderRadius: 4,
                    padding: '8px 12px',
                  }}>
                    <Text strong style={{ fontSize: 12, color: '#d46b08' }}>
                      可改善因素：
                    </Text>
                    {issue.contributing_factors.map((cf, cfIdx) => (
                      <div key={cfIdx} style={{ marginTop: 4 }}>
                        <Text style={{ fontSize: 12 }}>
                          - {cf.factor}: {cf.value} — {cf.explanation}
                        </Text>
                      </div>
                    ))}
                  </div>
                )}

                {/* Rationale */}
                <Paragraph style={{ marginBottom: 4 }}>
                  <Text type="secondary">建议理由：</Text>
                  {issue.recommendation_rationale}
                </Paragraph>

                <Paragraph style={{ marginBottom: 0 }}>
                  <Text type="secondary">建议方案：</Text>
                  {issue.recommendation}
                </Paragraph>

                <Tooltip title={issue.guideline_ref}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    参考: {issue.guideline_ref}
                  </Text>
                </Tooltip>
              </Space>
            </Card>
          );
        })}
      </div>
    );
  }

  // ── Risk Panel ─────────────────────────────────────────────────────────
  if (type === 'risk' && riskData) {
    const modifiableKeys = new Set(riskData.modifiable_factors.map(f => f.factor_key));

    return (
      <div>
        {/* Summary */}
        <Card
          style={{ marginBottom: 16 }}
          title={
            <Space>
              <SafetyCertificateOutlined />
              <span>风险评估分析依据</span>
            </Space>
          }
        >
          <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{riskData.summary}</Paragraph>
        </Card>

        {/* Contributing factors sorted by impact */}
        <Card title="风险因素明细" size="small" style={{ marginBottom: 16 }}>
          {riskData.contributing_factors.map((f, idx) => {
            const isModifiable = modifiableKeys.has(f.factor_key);
            return (
              <div
                key={idx}
                style={{
                  marginBottom: 12,
                  padding: '8px 12px',
                  borderRadius: 4,
                  background: isModifiable ? '#fffbe6' : 'transparent',
                  border: isModifiable ? '1px solid #ffe58f' : '1px solid transparent',
                }}
              >
                <Row justify="space-between" align="middle" style={{ marginBottom: 4 }}>
                  <Col>
                    <Space>
                      {isModifiable && (
                        <Tooltip title="可改善因素">
                          <BulbOutlined style={{ color: '#faad14' }} />
                        </Tooltip>
                      )}
                      <Text strong>{f.factor}</Text>
                    </Space>
                  </Col>
                  <Col>
                    <Text type="secondary">评分: {f.score}分</Text>
                  </Col>
                </Row>
                <Progress
                  percent={Math.round(f.impact_pct)}
                  size="small"
                  showInfo={false}
                  strokeColor={isModifiable ? '#faad14' : '#1890ff'}
                  trailColor="#f0f0f0"
                  style={{ marginBottom: 4 }}
                />
                <Row justify="space-between">
                  <Col>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      阈值: {f.threshold}
                    </Text>
                  </Col>
                  <Col>
                    <Text style={{ fontSize: 12 }}>
                      占风险权重 {Math.round(f.impact_pct)}%
                    </Text>
                  </Col>
                </Row>
                {f.actionable_advice && isModifiable && (
                  <div style={{ marginTop: 4 }}>
                    <Text style={{ fontSize: 12, color: '#d46b08' }}>
                      改善建议: {f.actionable_advice}
                    </Text>
                  </div>
                )}
              </div>
            );
          })}
        </Card>

        {/* Modifiable factors highlight */}
        {riskData.modifiable_factors.length > 0 && (
          <Card
            title="可改善因素"
            size="small"
            style={{ background: '#fffbe6', border: '1px solid #ffe58f' }}
          >
            {riskData.modifiable_factors.map((f, idx) => (
              <div key={idx} style={{ marginBottom: 8 }}>
                <Row justify="space-between">
                  <Text strong>{f.factor}</Text>
                  <Tag color="orange">评分 {f.score}分</Tag>
                </Row>
                {f.actionable_advice && (
                  <Paragraph style={{ fontSize: 12, color: '#d46b08', marginBottom: 0 }}>
                    {f.actionable_advice}
                  </Paragraph>
                )}
              </div>
            ))}
          </Card>
        )}
      </div>
    );
  }

  return (
    <Empty
      description="暂无分析依据数据"
      image={Empty.PRESENTED_IMAGE_SIMPLE}
    />
  );
}
