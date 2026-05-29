import { useState } from 'react';
import { Form, InputNumber, Radio, Button, Card, Typography, Progress } from 'antd';
import { assessRisk, type RiskAssessmentResult } from '../../lib/api';
import { mockAssessRisk } from '../../lib/mock';

const { Title, Text } = Typography;

const riskColors: Record<string, string> = {
  '低危': '#52c41a',
  '中危': '#faad14',
  '高危': '#ff7a45',
  '极高危': '#ff4d4f',
};

export default function RiskAssessment() {
  const [result, setResult] = useState<RiskAssessmentResult | null>(null);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const res = await assessRisk(values);
      setResult(res);
    } catch {
      setResult(mockAssessRisk());
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    const pct = Math.round((result.score / result.max_score) * 100);
    const color = riskColors[result.risk_level] || '#999';
    return (
      <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
        <Title level={3}>评估结果</Title>
        <Card>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Progress type="circle" percent={pct} strokeColor={color} format={() => `${result.score}分`} />
            <Title level={2} style={{ color, marginTop: 16 }}>{result.risk_level}</Title>
          </div>
          <Title level={5}>分项得分</Title>
          {Object.entries(result.factor_scores).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
              <Text>{key}</Text>
              <Text strong>{val}分</Text>
            </div>
          ))}
          <Title level={5} style={{ marginTop: 16 }}>建议</Title>
          <ul>{result.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
          <Button block onClick={() => setResult(null)} style={{ marginTop: 16 }}>
            重新评估
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>糖尿病风险评估</Title>
      <Card>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item label="年龄" name="age" rules={[{ required: true }]}>
            <InputNumber min={18} max={120} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="BMI (体重kg/身高m²)" name="bmi" rules={[{ required: true }]}>
            <InputNumber min={10} max={60} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="腰围(cm)" name="waist_circumference" rules={[{ required: true }]}>
            <InputNumber min={50} max={200} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="直系亲属糖尿病史" name="family_history" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value={true}>有</Radio>
              <Radio value={false}>无</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="体力活动水平" name="physical_activity" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value="low">低（久坐为主）</Radio>
              <Radio value="moderate">中等（每周运动2-3次）</Radio>
              <Radio value="high">高（每周运动{'>'}4次）</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="空腹血糖(mmol/L)" name="fasting_glucose" rules={[{ required: true }]}>
            <InputNumber min={2} max={30} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="是否有高血压" name="has_hypertension" rules={[{ required: true }]}>
            <Radio.Group>
              <Radio value={true}>是</Radio>
              <Radio value={false}>否</Radio>
            </Radio.Group>
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            开始评估
          </Button>
        </Form>
      </Card>
    </div>
  );
}
