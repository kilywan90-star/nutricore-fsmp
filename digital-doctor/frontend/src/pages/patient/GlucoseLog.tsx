import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Typography, Button, Form, InputNumber, Select, Input, Table, Statistic, Row, Col,
  Tag, Space, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, LineChartOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined,
} from '@ant-design/icons';
import { getGlucoseStats } from '../../lib/api';
import { mockGlucoseRecords, mockGlucoseStats, type GlucoseRecord } from '../../lib/mock';

const { Title, Text } = Typography;

const MEASURE_TYPES = [
  { value: 'fasting', label: '空腹血糖' },
  { value: 'pre_meal', label: '餐前血糖' },
  { value: 'post_prandial', label: '餐后血糖' },
  { value: 'bedtime', label: '睡前血糖' },
  { value: 'random', label: '随机血糖' },
];

function getMeasureTypeLabel(type: string): string {
  return MEASURE_TYPES.find(t => t.value === type)?.label || type;
}

function getGlucoseLevelTag(value: number) {
  if (value <= 3.9) return <Tag color="red">低血糖</Tag>;
  if (value < 6.1) return <Tag color="green">正常</Tag>;
  if (value < 7.0) return <Tag color="orange">偏高</Tag>;
  if (value < 11.1) return <Tag color="volcano">高血糖</Tag>;
  return <Tag color="red">严重高血糖</Tag>;
}

function getTrendIcon(direction: string) {
  switch (direction) {
    case 'rising': return <ArrowUpOutlined style={{ color: '#ff4d4f' }} />;
    case 'falling': return <ArrowDownOutlined style={{ color: '#52c41a' }} />;
    case 'stable': return <MinusOutlined style={{ color: '#1677ff' }} />;
    default: return null;
  }
}

function getTrendLabel(direction: string): string {
  switch (direction) {
    case 'rising': return '上升趋势';
    case 'falling': return '下降趋势';
    case 'stable': return '平稳';
    case 'insufficient_data': return '数据不足';
    default: return direction;
  }
}

function computeTrend(records: GlucoseRecord[]): { direction: string; change_rate: number | null } {
  const sorted = [...records]
    .filter(r => r.measure_type === 'fasting')
    .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());

  if (sorted.length < 3) return { direction: 'insufficient_data', change_rate: null };

  const recent = sorted.slice(-3);
  const values = recent.map(r => r.value_mmol_l);

  if (values[0] < values[1] && values[1] < values[2]) {
    const rate = ((values[2] - values[0]) / values[0]) * 100;
    return { direction: 'rising', change_rate: Math.round(rate * 10) / 10 };
  }
  if (values[0] > values[1] && values[1] > values[2]) {
    const rate = ((values[0] - values[2]) / values[0]) * 100;
    return { direction: 'falling', change_rate: Math.round(rate * 10) / 10 };
  }
  return { direction: 'stable', change_rate: 0 };
}

export default function GlucoseLog() {
  const nav = useNavigate();
  const [records, setRecords] = useState<GlucoseRecord[]>(mockGlucoseRecords());
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const stats = useMemo(() => {
    const values = records.map(r => r.value_mmol_l);
    return mockGlucoseStats(); // mock stats as default structure
  }, [records]);

  const computedStats = useMemo(() => {
    const values = records.map(r => r.value_mmol_l);
    if (values.length === 0) return { count: 0, avg: null, max: null, min: null };
    const n = values.length;
    const avg = values.reduce((a, b) => a + b, 0) / n;
    return {
      count: n,
      avg: Math.round(avg * 10) / 10,
      max: Math.max(...values),
      min: Math.min(...values),
    };
  }, [records]);

  const trend = useMemo(() => computeTrend(records), [records]);

  const addRecord = (values: any) => {
    const newRecord: GlucoseRecord = {
      id: `manual-${Date.now()}`,
      value_mmol_l: values.value_mmol_l,
      measure_type: values.measure_type,
      recorded_at: new Date().toISOString(),
      notes: values.notes || '',
    };
    setRecords(prev => [newRecord, ...prev]);
    form.resetFields();
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'recorded_at',
      key: 'time',
      width: 160,
      render: (val: string) => {
        const d = new Date(val);
        return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
      },
    },
    {
      title: '类型',
      dataIndex: 'measure_type',
      key: 'type',
      width: 100,
      render: (val: string) => <Tag>{getMeasureTypeLabel(val)}</Tag>,
    },
    {
      title: '血糖值 (mmol/L)',
      dataIndex: 'value_mmol_l',
      key: 'value',
      width: 120,
      render: (val: number) => <Text strong>{val}</Text>,
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_: any, record: GlucoseRecord) => getGlucoseLevelTag(record.value_mmol_l),
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      render: (val: string) => val ? <Text type="secondary">{val}</Text> : <Text type="secondary">-</Text>,
    },
  ];

  const fastingRecords = records.filter(r => r.measure_type === 'fasting');
  const fastingValues = fastingRecords.map(r => r.value_mmol_l);
  const fastingStats = fastingValues.length > 0 ? {
    avg: Math.round(fastingValues.reduce((a, b) => a + b, 0) / fastingValues.length * 10) / 10,
    max: Math.max(...fastingValues),
    min: Math.min(...fastingValues),
    count: fastingValues.length,
  } : { avg: null, max: null, min: null, count: 0 };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} type="link" onClick={() => nav('/patient')} style={{ padding: 0, marginBottom: 16 }}>
        返回首页
      </Button>

      <Title level={3}><LineChartOutlined /> 血糖记录</Title>

      <Card title="记录血糖" size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={addRecord} style={{ flexWrap: 'wrap', gap: 8 }}>
          <Form.Item name="value_mmol_l" rules={[{ required: true, message: '请输入血糖值' }]}>
            <InputNumber min={1} max={40} step={0.1} placeholder="血糖值" style={{ width: 120 }} addonAfter="mmol/L" />
          </Form.Item>
          <Form.Item name="measure_type" rules={[{ required: true, message: '选择类型' }]} initialValue="fasting">
            <Select options={MEASURE_TYPES} style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="notes">
            <Input placeholder="备注（可选）" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>记录</Button>
          </Form.Item>
        </Form>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="总记录数" value={computedStats.count} suffix="次" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="平均血糖" value={computedStats.avg ?? '-'} suffix={computedStats.avg != null ? 'mmol/L' : ''} precision={1} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="最高值" value={computedStats.max ?? '-'} suffix={computedStats.max != null ? 'mmol/L' : ''} precision={1} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="最低值" value={computedStats.min ?? '-'} suffix={computedStats.min != null ? 'mmol/L' : ''} precision={1} />
          </Card>
        </Col>
      </Row>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>趋势方向：</Text>
          <Space>
            {getTrendIcon(trend.direction)}
            <Text>{getTrendLabel(trend.direction)}</Text>
          </Space>
          {trend.change_rate != null && (
            <Tag color={trend.direction === 'rising' ? 'red' : trend.direction === 'falling' ? 'green' : 'blue'}>
              {trend.change_rate > 0 ? '+' : ''}{trend.change_rate}%
            </Tag>
          )}
        </Space>
      </Card>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}><Statistic title="空腹平均" value={fastingStats.avg ?? '-'} precision={1} suffix="mmol/L" /></Col>
          <Col span={6}><Statistic title="空腹最高" value={fastingStats.max ?? '-'} precision={1} suffix="mmol/L" /></Col>
          <Col span={6}><Statistic title="空腹最低" value={fastingStats.min ?? '-'} precision={1} suffix="mmol/L" /></Col>
          <Col span={6}><Statistic title="空腹记录" value={fastingStats.count} suffix="次" /></Col>
        </Row>
      </Card>

      <Card title="血糖记录列表">
        {records.length === 0 ? (
          <Empty description="暂无血糖记录" />
        ) : (
          <Table
            dataSource={records}
            columns={columns}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            scroll={{ x: 600 }}
          />
        )}
      </Card>
    </div>
  );
}
