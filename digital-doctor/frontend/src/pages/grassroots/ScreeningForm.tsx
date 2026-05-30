import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Radio, Switch, Card, Typography, Result, Spin, message } from 'antd';
import { submitScreening, type ScreeningResult } from '../../lib/api';

const { Title } = Typography;

export default function ScreeningForm() {
  const nav = useNavigate();
  const [form] = Form.useForm();
  const [result, setResult] = useState<ScreeningResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      const res = await submitScreening({
        name: values.name,
        village: values.village,
        age: values.age,
        gender: values.gender,
        waist_circumference: values.waist_circumference,
        fasting_glucose: values.fasting_glucose,
        systolic_bp: values.systolic_bp ?? 120,
        diastolic_bp: values.diastolic_bp ?? 80,
        family_history: values.family_history ?? false,
      });
      setResult(res);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '提交失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    form.resetFields();
  };

  if (result) {
    const isHighRisk = result.referral_needed;
    return (
      <Card>
        <Result
          status={isHighRisk ? 'warning' : 'success'}
          title={`风险等级：${result.risk_level === 'low' ? '低危' : result.risk_level === 'moderate' ? '中危' : result.risk_level === 'high' ? '高危' : '极高危'}`}
          subTitle={
            <div style={{ textAlign: 'left' }}>
              <p>风险评分：{result.risk_score} / {result.max_score}</p>
              <p style={{ color: isHighRisk ? '#ff4d4f' : '#52c41a' }}>
                建议：{result.recommendation}
              </p>
              {result.factor_scores && (
                <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                  各因素评分：{JSON.stringify(result.factor_scores)}
                </div>
              )}
            </div>
          }
          extra={[
            <Button key="back" size="large" onClick={handleReset}>
              再次筛查
            </Button>,
            <Button
              key="home"
              type="primary"
              size="large"
              onClick={() => nav('/grassroots')}
            >
              返回首页
            </Button>,
          ]}
        />
      </Card>
    );
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>社区筛查登记</Title>
      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit} size="large">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="请输入姓名" />
          </Form.Item>

          <Form.Item name="village" label="村/社区" rules={[{ required: true, message: '请输入村或社区名称' }]}>
            <Input placeholder="如：张家村" />
          </Form.Item>

          <Form.Item name="age" label="年龄" rules={[{ required: true, message: '请输入年龄' }]}>
            <Input type="number" min={18} max={120} placeholder="18-120" />
          </Form.Item>

          <Form.Item name="gender" label="性别" rules={[{ required: true, message: '请选择性别' }]}>
            <Radio.Group buttonStyle="solid" style={{ width: '100%' }}>
              <Radio.Button value="M" style={{ width: '50%', textAlign: 'center' }}>男</Radio.Button>
              <Radio.Button value="F" style={{ width: '50%', textAlign: 'center' }}>女</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="waist_circumference" label="腰围 (cm)" rules={[{ required: true, message: '请输入腰围' }]}>
            <Input type="number" min={50} max={200} step={0.1} placeholder="如：85" />
          </Form.Item>

          <Form.Item name="fasting_glucose" label="空腹血糖 (mmol/L)" rules={[{ required: true, message: '请输入空腹血糖' }]}>
            <Input type="number" min={2} max={30} step={0.1} placeholder="如：6.5" />
          </Form.Item>

          <Form.Item name="systolic_bp" label="收缩压 (mmHg)">
            <Input type="number" min={60} max={250} placeholder="默认120" />
          </Form.Item>

          <Form.Item name="diastolic_bp" label="舒张压 (mmHg)">
            <Input type="number" min={30} max={150} placeholder="默认80" />
          </Form.Item>

          <Form.Item name="family_history" label="糖尿病家族史" valuePropName="checked">
            <Switch checkedChildren="有" unCheckedChildren="无" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={submitting} style={{ height: 50 }}>
              提交筛查
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
