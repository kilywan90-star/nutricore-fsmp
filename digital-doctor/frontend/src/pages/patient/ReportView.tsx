import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form, Select, InputNumber, Button, Card, Typography, Tag, Result, Space, Row, Col,
} from 'antd';
import {
  ArrowLeftOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { interpretReport, type ReportInterpretResult } from '../../lib/api';
import { mockInterpretReport } from '../../lib/mock';

const { Title, Text } = Typography;

const REPORT_TYPES = [
  { value: 'blood_glucose_panel', label: '血糖全套' },
  { value: 'hba1c_only', label: '糖化血红蛋白' },
  { value: 'lipid_panel', label: '血脂四项' },
];

const GLUCOSE_FIELDS = [
  { name: 'fpg', label: '空腹血糖 FPG (mmol/L)', min: 2, max: 30 },
  { name: 'hba1c', label: '糖化血红蛋白 HbA1c (%)', min: 3, max: 20 },
  { name: 'ppg_2h', label: '餐后2h血糖 (mmol/L)', min: 2, max: 40 },
];

const LIPID_FIELDS = [
  { name: 'tc', label: '总胆固醇 TC (mmol/L)', min: 2, max: 15 },
  { name: 'ldl', label: '低密度脂蛋白 LDL (mmol/L)', min: 0.5, max: 10 },
  { name: 'hdl', label: '高密度脂蛋白 HDL (mmol/L)', min: 0.3, max: 5 },
  { name: 'tg', label: '甘油三酯 TG (mmol/L)', min: 0.3, max: 20 },
];

const HBA1C_FIELDS = [
  { name: 'hba1c', label: '糖化血红蛋白 HbA1c (%)', min: 3, max: 20 },
];

const statusColor: Record<string, string> = {
  normal: 'green',
  impaired: 'orange',
  abnormal: 'red',
  unknown: 'default',
};

const statusLabel: Record<string, string> = {
  normal: '正常',
  impaired: '临界异常',
  abnormal: '异常',
  unknown: '未知',
};

export default function ReportView() {
  const nav = useNavigate();
  const [reportType, setReportType] = useState<string>('blood_glucose_panel');
  const [result, setResult] = useState<ReportInterpretResult | null>(null);
  const [loading, setLoading] = useState(false);

  const getFields = () => {
    switch (reportType) {
      case 'blood_glucose_panel': return GLUCOSE_FIELDS;
      case 'hba1c_only': return HBA1C_FIELDS;
      case 'lipid_panel': return LIPID_FIELDS;
      default: return GLUCOSE_FIELDS;
    }
  };

  const onFinish = async (values: any) => {
    setLoading(true);
    const results: Record<string, number> = {};
    getFields().forEach(f => { if (values[f.name] != null) results[f.name] = values[f.name]; });

    try {
      const res = await interpretReport(reportType, results);
      setResult(res);
    } catch {
      setResult(mockInterpretReport(reportType, results));
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
        <Button icon={<ArrowLeftOutlined />} type="link" onClick={() => setResult(null)} style={{ padding: 0, marginBottom: 16 }}>
          返回输入
        </Button>
        <Title level={3}>AI报告解读结果</Title>
        <Card>
          <Result
            status={result.status === 'normal' ? 'success' : result.status === 'impaired' ? 'warning' : 'error'}
            title={
              <Tag color={statusColor[result.status]} style={{ fontSize: 16, padding: '4px 16px' }}>
                {result.status_label}
              </Tag>
            }
          />
          <Title level={5}>检查项目</Title>
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            {result.items.map(item => (
              <Col key={item.item}>
                <Tag color={statusColor[item.status]}>
                  {item.item}: {item.value} ({statusLabel[item.status]})
                </Tag>
              </Col>
            ))}
          </Row>
          <Title level={5}>AI解读</Title>
          <Card size="small" style={{ background: '#f6f8fa', marginBottom: 16 }}>
            <Text>{result.interpretation}</Text>
          </Card>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} type="link" onClick={() => nav('/patient')} style={{ padding: 0, marginBottom: 16 }}>
        返回首页
      </Button>
      <Title level={3}>AI报告解读</Title>
      <Card>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item label="报告类型" required>
            <Select value={reportType} onChange={setReportType} options={REPORT_TYPES} />
          </Form.Item>
          {getFields().map(f => (
            <Form.Item key={f.name} label={f.label} name={f.name} rules={[{ required: true, message: `请输入${f.label}` }]}>
              <InputNumber min={f.min} max={f.max} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
          ))}
          <Button type="primary" htmlType="submit" block loading={loading} icon={<FileTextOutlined />}>
            AI解读报告
          </Button>
        </Form>
      </Card>
    </div>
  );
}
