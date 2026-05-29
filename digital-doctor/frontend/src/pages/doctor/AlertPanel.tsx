import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Select, Button, Typography, Tag, Space, message, Spin, Empty, Row,
} from 'antd';
import { ArrowLeftOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getAllAlerts, acknowledgeAlert, type DoctorAlertItem } from '../../lib/api';
import AlertBadge from '../../components/AlertBadge';

const { Title } = Typography;

export default function AlertPanel() {
  const nav = useNavigate();
  const [alerts, setAlerts] = useState<DoctorAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | undefined>(undefined);
  const [acknowledging, setAcknowledging] = useState<Set<string>>(new Set());

  const fetchAlerts = useCallback(async (severity?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAllAlerts({ severity, page_size: 200 });
      const items = result?.items || result?.alerts || [];
      setAlerts(items);
    } catch (err: any) {
      setError(err?.message || '加载预警失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts(severityFilter);
  }, [severityFilter, fetchAlerts]);

  const handleAcknowledge = async (alertId: string) => {
    setAcknowledging((prev) => new Set(prev).add(alertId));
    try {
      await acknowledgeAlert(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
      );
      message.success('预警已确认');
    } catch (err: any) {
      message.error(err?.message || '确认失败');
    } finally {
      setAcknowledging((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  const columns: ColumnsType<DoctorAlertItem> = [
    {
      title: '患者ID',
      dataIndex: 'patient_id',
      key: 'patient_id',
      width: 120,
      render: (id: string) => (
        <a onClick={() => nav(`/doctor/patients/${id}`)}>
          {id?.slice(0, 8)}...
        </a>
      ),
    },
    {
      title: '预警类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 140,
      render: (t: string) => {
        const labels: Record<string, string> = {
          severe_hyperglycemia: '严重高血糖',
          hypoglycemia: '低血糖',
          consecutive_high_fpg: '空腹血糖偏高',
          missed_logging: '血糖监测缺失',
          hba1c_high: 'HbA1c偏高',
          missed_medication: '漏服药物',
        };
        return labels[t] || t;
      },
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (s: string) => (
        <AlertBadge severity={s as 'info' | 'warning' | 'critical'}>
          {s === 'critical' ? '危急' : s === 'warning' ? '预警' : '信息'}
        </AlertBadge>
      ),
      filters: [
        { text: '危急', value: 'critical' },
        { text: '预警', value: 'warning' },
        { text: '信息', value: 'info' },
      ],
      onFilter: (value, record) => record.severity === value,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 180,
    },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'acknowledged',
      key: 'acknowledged',
      width: 100,
      render: (ack: boolean) =>
        ack ? (
          <Tag color="green">已确认</Tag>
        ) : (
          <Tag color="red">未确认</Tag>
        ),
      filters: [
        { text: '未确认', value: false },
        { text: '已确认', value: true },
      ],
      onFilter: (value, record) => record.acknowledged === value,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
      sorter: (a, b) => dayjs(a.created_at).valueOf() - dayjs(b.created_at).valueOf(),
      defaultSortOrder: 'descend',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: DoctorAlertItem) =>
        !record.acknowledged ? (
          <Button
            type="link"
            size="small"
            icon={<CheckCircleOutlined />}
            loading={acknowledging.has(record.id)}
            onClick={(e) => {
              e.stopPropagation();
              handleAcknowledge(record.id);
            }}
          >
            确认
          </Button>
        ) : null,
    },
  ];

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav('/doctor')}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>预警中心</Title>
        {unacknowledgedCount > 0 && (
          <Tag color="red" style={{ marginLeft: 12 }}>
            未确认 {unacknowledgedCount} 条
          </Tag>
        )}
      </Row>

      <div style={{ marginBottom: 16 }}>
        <Space>
          <span>按严重程度筛选：</span>
          <Select
            allowClear
            placeholder="全部"
            style={{ width: 120 }}
            value={severityFilter}
            onChange={(val) => setSeverityFilter(val)}
            options={[
              { label: '危急', value: 'critical' },
              { label: '预警', value: 'warning' },
              { label: '信息', value: 'info' },
            ]}
          />
          {alerts.length > 0 && (
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {alerts.length} 条记录
            </span>
          )}
        </Space>
      </div>

      {error ? (
        <Empty description={error} />
      ) : (
        <Table<DoctorAlertItem>
          columns={columns}
          dataSource={alerts}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条预警`,
          }}
          locale={{ emptyText: '暂无预警' }}
        />
      )}
    </div>
  );
}

