import { useEffect, useState, useCallback } from 'react';
import {
  Table, Select, Typography, Button, Space, DatePicker, Spin, Empty, Tag,
} from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getAuditLogs, type AuditLogItem } from '../../lib/api';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const ACTION_LABELS: Record<string, string> = {
  VIEW: '查看',
  CREATE: '创建',
  UPDATE: '更新',
  DELETE: '删除',
  ASSIGN: '分配',
  EXPORT: '导出',
};

const RESOURCE_LABELS: Record<string, string> = {
  patient: '患者',
  medication: '用药',
  report: '报告',
  alert: '预警',
  department: '科室',
  doctor_profile: '医生',
};

const ACTION_COLORS: Record<string, string> = {
  VIEW: 'blue',
  CREATE: 'green',
  UPDATE: 'orange',
  DELETE: 'red',
  ASSIGN: 'purple',
  EXPORT: 'cyan',
};

export default function AuditLogViewer() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filterAction, setFilterAction] = useState<string | undefined>();
  const [filterResource, setFilterResource] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { page, page_size: pageSize };
      if (filterAction) params.action = filterAction;
      if (filterResource) params.resource_type = filterResource;
      const data = await getAuditLogs(params);
      let items = data.items;

      // Client-side date range filter if needed
      if (dateRange && dateRange[0] && dateRange[1]) {
        const start = dateRange[0].startOf('day').valueOf();
        const end = dateRange[1].endOf('day').valueOf();
        items = items.filter((item: AuditLogItem) => {
          const t = dayjs(item.timestamp).valueOf();
          return t >= start && t <= end;
        });
      }

      setLogs(items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterAction, filterResource, dateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExportCSV = () => {
    if (logs.length === 0) return;

    const headers = ['时间', '用户ID', '操作', '资源类型', '资源ID', '详情', 'IP地址'];
    const rows = logs.map((log) => [
      dayjs(log.timestamp).format('YYYY-MM-DD HH:mm:ss'),
      log.user_id || '匿名',
      ACTION_LABELS[log.action] || log.action,
      RESOURCE_LABELS[log.resource_type] || log.resource_type,
      log.resource_id || '',
      log.details ? JSON.stringify(log.details) : '',
      log.ip_address || '',
    ]);

    const csvContent =
      '﻿' +
      [headers, ...rows]
        .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${dayjs().format('YYYYMMDD-HHmmss')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 170,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.timestamp).valueOf() - dayjs(b.timestamp).valueOf(),
      defaultSortOrder: 'descend',
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      render: (v: string | null) =>
        v ? <code>{v.slice(0, 8)}...</code> : <Tag>匿名</Tag>,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (v: string) => (
        <Tag color={ACTION_COLORS[v] || 'default'}>
          {ACTION_LABELS[v] || v}
        </Tag>
      ),
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 100,
      render: (v: string) => RESOURCE_LABELS[v] || v,
    },
    {
      title: '资源ID',
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 120,
      render: (v: string | null) =>
        v ? <code style={{ fontSize: 12 }}>{v.slice(0, 16)}...</code> : '-',
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
      render: (v: Record<string, unknown> | null) =>
        v ? (
          <code style={{ fontSize: 11, maxWidth: 200, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {JSON.stringify(v)}
          </code>
        ) : '-',
    },
  ];

  if (error && logs.length === 0) {
    return <Empty description={error} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Title level={4} style={{ margin: 0 }}>操作日志</Title>
        <Space wrap>
          <RangePicker
            onChange={(dates) => {
              setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null);
              setPage(1);
            }}
            allowClear
            style={{ width: 240 }}
          />
          <Select
            allowClear
            placeholder="操作类型"
            style={{ width: 110 }}
            value={filterAction}
            onChange={(val) => { setFilterAction(val); setPage(1); }}
            options={Object.entries(ACTION_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Select
            allowClear
            placeholder="资源类型"
            style={{ width: 110 }}
            value={filterResource}
            onChange={(val) => { setFilterResource(val); setPage(1); }}
            options={Object.entries(RESOURCE_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Button icon={<DownloadOutlined />} onClick={handleExportCSV}>
            导出CSV
          </Button>
        </Space>
      </div>

      <Table<AuditLogItem>
        columns={columns}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条记录`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        locale={{ emptyText: '暂无操作日志' }}
      />
    </div>
  );
}
