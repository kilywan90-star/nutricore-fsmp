import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Input, Typography, Button, Badge, Spin, Empty, Row } from 'antd';
import { SearchOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getPatients, type PatientListItem } from '../../lib/api';

const { Title } = Typography;

export default function PatientList() {
  const nav = useNavigate();
  const [data, setData] = useState<PatientListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');

  const fetchData = useCallback(async (p: number, ps: number, s: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getPatients(p, ps, s);
      setData(result.items);
      setTotal(result.total);
    } catch (err: any) {
      setError(err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(page, pageSize, search);
  }, [page, pageSize, search, fetchData]);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const columns: ColumnsType<PatientListItem> = [
    {
      title: '患者ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => id.slice(0, 8) + '...',
    },
    {
      title: '性别',
      dataIndex: 'gender',
      key: 'gender',
      width: 60,
      render: (g: string) => (g === 'M' ? '男' : g === 'F' ? '女' : g),
    },
    {
      title: '年龄',
      key: 'age',
      width: 60,
      render: (_: any, record: PatientListItem) => {
        const currentYear = dayjs().year();
        return currentYear - record.birth_year;
      },
      sorter: (a, b) => b.birth_year - a.birth_year,
    },
    {
      title: '糖尿病类型',
      dataIndex: 'diabetes_type',
      key: 'diabetes_type',
      width: 120,
      render: (t: string) => t === 'type2' ? '2型' : t === 'type1' ? '1型' : t,
    },
    {
      title: '最近血糖',
      dataIndex: 'latest_glucose',
      key: 'latest_glucose',
      width: 100,
      render: (v: number | null) =>
        v != null ? (
          <span style={{ color: v > 10.0 ? '#ff4d4f' : v < 3.9 ? '#faad14' : '#52c41a' }}>
            {v} mmol/L
          </span>
        ) : (
          <span style={{ color: '#999' }}>-</span>
        ),
      sorter: (a, b) => (a.latest_glucose ?? -1) - (b.latest_glucose ?? -1),
    },
    {
      title: '预警',
      dataIndex: 'alert_count',
      key: 'alert_count',
      width: 80,
      render: (count: number) =>
        count > 0 ? <Badge count={count} overflowCount={99} /> : <span style={{ color: '#999' }}>0</span>,
      sorter: (a, b) => a.alert_count - b.alert_count,
    },
    {
      title: 'HbA1c目标',
      dataIndex: 'hba1c_target',
      key: 'hba1c_target',
      width: 100,
      render: (t: number) => `${t}%`,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Row align="middle" style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => nav('/doctor')}
          style={{ marginRight: 16 }}
        >
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>患者管理</Title>
      </Row>

      <div style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="搜索患者ID..."
          allowClear
          onSearch={handleSearch}
          style={{ maxWidth: 400 }}
          prefix={<SearchOutlined />}
        />
      </div>

      {error ? (
        <Empty description={error} />
      ) : (
        <Table<PatientListItem>
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 位患者`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          onRow={(record) => ({
            onClick: () => nav(`/doctor/patients/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          locale={{ emptyText: '暂无患者数据' }}
        />
      )}
    </div>
  );
}

