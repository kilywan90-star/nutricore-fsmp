import { useEffect, useState, useCallback } from 'react';
import {
  Table, Select, Typography, Button, Tag, Space, Spin, Empty, message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  getAdminDoctors,
  getAdminDepartments,
  assignDoctorDepartment,
  toggleDoctorActive,
  type AdminDoctorItem,
  type DepartmentItem,
} from '../../lib/api';

const { Title } = Typography;

export default function DoctorManager() {
  const [doctors, setDoctors] = useState<AdminDoctorItem[]>([]);
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterDeptId, setFilterDeptId] = useState<string | undefined>(
    new URLSearchParams(window.location.search).get('department_id') || undefined
  );
  const [assigningId, setAssigningId] = useState<string | null>(null);

  const fetchData = useCallback(async (p: number, ps: number, deptId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const [docData, deptData] = await Promise.all([
        getAdminDoctors({ page: p, page_size: ps, department_id: deptId }),
        getAdminDepartments(),
      ]);
      setDoctors(docData.items);
      setTotal(docData.total);
      setDepartments(deptData.items);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(page, pageSize, filterDeptId);
  }, [page, pageSize, filterDeptId, fetchData]);

  const handleAssignDept = async (doctorId: string, departmentId: string) => {
    try {
      setAssigningId(doctorId);
      await assignDoctorDepartment(doctorId, departmentId);
      message.success('科室分配成功');
      fetchData(page, pageSize, filterDeptId);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '分配失败');
    } finally {
      setAssigningId(null);
    }
  };

  const handleToggleActive = async (doctorId: string) => {
    try {
      await toggleDoctorActive(doctorId);
      message.success('状态已更新');
      fetchData(page, pageSize, filterDeptId);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失败');
    }
  };

  const columns: ColumnsType<AdminDoctorItem> = [
    {
      title: '姓名/职称',
      key: 'info',
      width: 180,
      render: (_: any, record: AdminDoctorItem) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.title}</div>
          <div style={{ fontSize: 12, color: '#999' }}>ID: {record.id.slice(0, 8)}...</div>
        </div>
      ),
    },
    {
      title: '科室',
      key: 'department',
      width: 220,
      render: (_: any, record: AdminDoctorItem) => (
        <Select
          style={{ width: 200 }}
          value={record.department_id}
          loading={assigningId === record.id}
          onChange={(val) => handleAssignDept(record.id, val)}
          options={departments
            .filter((d) => d.is_active)
            .map((d) => ({ value: d.id, label: `${d.name} (${d.code})` }))}
        />
      ),
    },
    {
      title: '科主任',
      dataIndex: 'is_department_head',
      key: 'is_department_head',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="gold">科主任</Tag> : <span style={{ color: '#999' }}>-</span>),
    },
    {
      title: '管理患者',
      dataIndex: 'patient_count',
      key: 'patient_count',
      width: 90,
      sorter: (a, b) => a.patient_count - b.patient_count,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      width: 150,
      render: (v: string | null) =>
        v ? dayjs(v).format('YYYY-MM-DD HH:mm') : <span style={{ color: '#999' }}>从未登录</span>,
      sorter: (a, b) => {
        if (!a.last_login_at) return 1;
        if (!b.last_login_at) return -1;
        return dayjs(a.last_login_at).valueOf() - dayjs(b.last_login_at).valueOf();
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: any, record: AdminDoctorItem) => (
        <Button
          type="link"
          size="small"
          danger={record.is_active}
          onClick={() => handleToggleActive(record.id)}
        >
          {record.is_active ? '停用' : '启用'}
        </Button>
      ),
    },
  ];

  if (error && doctors.length === 0) {
    return <Empty description={error} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>医生管理</Title>
        <Space>
          <Select
            allowClear
            placeholder="按科室筛选"
            style={{ width: 200 }}
            value={filterDeptId}
            onChange={(val) => {
              setFilterDeptId(val);
              setPage(1);
            }}
            options={departments.map((d) => ({ value: d.id, label: d.name }))}
          />
        </Space>
      </div>

      <Table<AdminDoctorItem>
        columns={columns}
        dataSource={doctors}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 位医生`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        locale={{ emptyText: '暂无医生数据' }}
      />
    </div>
  );
}
