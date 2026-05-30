import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Button, Modal, Form, Input, Switch, Typography, Space, Popconfirm, Spin, Empty, Tag,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  getAdminDepartments,
  createAdminDepartment,
  updateAdminDepartment,
  deleteAdminDepartment,
  type DepartmentItem,
} from '../../lib/api';

const { Title } = Typography;

export default function DepartmentManager() {
  const nav = useNavigate();
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<DepartmentItem | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminDepartments();
      setDepartments(data.items);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAdd = () => {
    setEditingDept(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const handleEdit = (record: DepartmentItem) => {
    setEditingDept(record);
    form.setFieldsValue({
      name: record.name,
      code: record.code,
      is_active: record.is_active,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAdminDepartment(id);
      fetchData();
    } catch (err: any) {
      Modal.error({ title: '删除失败', content: err?.response?.data?.detail || '无法删除' });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      if (editingDept) {
        await updateAdminDepartment(editingDept.id, values);
      } else {
        await createAdminDepartment(values);
      }
      setModalOpen(false);
      fetchData();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        Modal.error({ title: '保存失败', content: err.response.data.detail });
      }
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<DepartmentItem> = [
    { title: '科室名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '科室代码', dataIndex: 'code', key: 'code', width: 120 },
    {
      title: '医生数',
      dataIndex: 'doctor_count',
      key: 'doctor_count',
      width: 80,
      sorter: (a, b) => a.doctor_count - b.doctor_count,
    },
    {
      title: '患者数',
      dataIndex: 'patient_count',
      key: 'patient_count',
      width: 80,
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
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: DepartmentItem) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除此科室？"
            description={`科室 "${record.name}" 将被删除`}
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (error && departments.length === 0) {
    return <Empty description={error} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>科室管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增科室
        </Button>
      </div>

      <Table<DepartmentItem>
        columns={columns}
        dataSource={departments}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 个科室` }}
        onRow={(record) => ({
          onClick: () => nav(`/admin/doctors?department_id=${record.id}`),
          style: { cursor: 'pointer' },
        })}
        locale={{ emptyText: '暂无科室数据' }}
      />

      <Modal
        title={editingDept ? '编辑科室' : '新增科室'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="科室名称"
            rules={[{ required: true, message: '请输入科室名称' }]}
          >
            <Input maxLength={100} placeholder="如：内分泌科" />
          </Form.Item>
          <Form.Item
            name="code"
            label="科室代码"
            rules={[
              { required: true, message: '请输入科室代码' },
              { pattern: /^[A-Z0-9_-]+$/, message: '仅支持大写字母、数字、下划线、连字符' },
            ]}
          >
            <Input maxLength={50} placeholder="如：ENDO" disabled={!!editingDept} />
          </Form.Item>
          {editingDept && (
            <Form.Item name="is_active" label="启用状态" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
