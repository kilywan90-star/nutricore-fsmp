import React, { useState } from 'react'
import { Button, Card, Table, Tag, Space, Modal, Form, Input, Select, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, CopyOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
interface Template {
  id: number
  name: string
  industry: string
  type: string
  description: string
  is_builtin: boolean
  created_at: string
  updated_at: string
}
const TemplateList: React.FC = () => {
  const [form] = Form.useForm()
  const [templates, setTemplates] = useState<Template[]>([
    {
      id: 1,
      name: '政府采购通用标书模板',
      industry: '通用',
      type: '政府采购',
      description: '适用于各类政府采购项目的通用标书模板，包含商务标、技术标、价格标完整结构',
      is_builtin: true,
      created_at: '2024-01-01 00:00:00',
      updated_at: '2024-01-01 00:00:00'
    },
    {
      id: 2,
      name: '建筑工程类标书模板',
      industry: '建筑工程',
      type: '工程建设',
      description: '适用于房屋建筑、市政工程等建筑类项目的标书模板',
      is_builtin: true,
      created_at: '2024-01-01 00:00:00',
      updated_at: '2024-01-01 00:00:00'
    },
    {
      id: 3,
      name: 'IT信息化项目标书模板',
      industry: 'IT/互联网',
      type: '服务类',
      description: '适用于软件开发、系统集成、信息化建设等IT类项目的标书模板',
      is_builtin: true,
      created_at: '2024-01-01 00:00:00',
      updated_at: '2024-01-01 00:00:00'
    }
  ])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const handleCreateTemplate = () => {
    setEditingTemplate(null)
    form.resetFields()
    setModalVisible(true)
  }
  const handleEditTemplate = (template: Template) => {
    if (template.is_builtin) {
      message.warning('内置模板不可编辑，请复制后修改')
      return
    }
    setEditingTemplate(template)
    form.setFieldsValue(template)
    setModalVisible(true)
  }
  const handleCopyTemplate = (template: Template) => {
    const newTemplate: Template = {
      id: templates.length > 0 ? Math.max(...templates.map(t => t.id)) + 1 : 1,
      name: `${template.name} - 副本`,
      industry: template.industry,
      type: template.type,
      description: template.description,
      is_builtin: false,
      created_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      updated_at: dayjs().format('YYYY-MM-DD HH:mm:ss')
    }
    setTemplates([newTemplate, ...templates])
    message.success('模板复制成功')
  }
  const handleDeleteTemplate = (id: number) => {
    const template = templates.find(t => t.id === id)
    if (template?.is_builtin) {
      message.error('内置模板不可删除')
      return
    }
    setTemplates(templates.filter(t => t.id !== id))
    message.success('删除成功')
  }
  const handleSubmitTemplate = (values: any) => {
    if (editingTemplate) {
      setTemplates(templates.map(t => t.id === editingTemplate.id ? { ...t, ...values } : t))
      message.success('模板更新成功')
    } else {
      const newTemplate: Template = {
        id: templates.length > 0 ? Math.max(...templates.map(t => t.id)) + 1 : 1,
        ...values,
        is_builtin: false,
        created_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
        updated_at: dayjs().format('YYYY-MM-DD HH:mm:ss')
      }
      setTemplates([newTemplate, ...templates])
      message.success('模板创建成功')
    }
    setModalVisible(false)
  }
  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      width: 240,
      render: (text: string, record: Template) => (
        <span>
          {text}
          {record.is_builtin && <Tag color="blue" style={{ marginLeft: 8 }}>内置</Tag>}
        </span>
      )
    },
    {
      title: '适用行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 120
    },
    {
      title: '模板类型',
      dataIndex: 'type',
      key: 'type',
      width: 120
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 150,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm')
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: any, record: Template) => (
        <Space size="small">
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopyTemplate(record)}
          >
            复制
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditTemplate(record)}
            disabled={record.is_builtin}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个模板吗？"
            description="删除后模板将无法恢复，请谨慎操作。"
            onConfirm={() => handleDeleteTemplate(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={record.is_builtin}
          >
            <Button danger size="small" icon={<DeleteOutlined />} disabled={record.is_builtin}>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ]
  return (
    <div className="page-container">
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="page-title">模板管理</div>
            <div className="page-subtitle">管理各类标书模板，内置模板不可编辑，可以复制后自定义修改</div>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateTemplate}>
            新建模板
          </Button>
        </div>
      </div>
      <Card className="card-container">
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个模板`
          }}
        />
      </Card>
      <Modal
        title={editingTemplate ? '编辑模板' : '新建模板'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmitTemplate}
        >
          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          <Form.Item
            label="适用行业"
            name="industry"
            rules={[{ required: true, message: '请选择适用行业' }]}
          >
            <Select placeholder="请选择适用行业">
              <Select.Option value="通用">通用</Select.Option>
              <Select.Option value="IT/互联网">IT/互联网</Select.Option>
              <Select.Option value="建筑工程">建筑工程</Select.Option>
              <Select.Option value="医疗健康">医疗健康</Select.Option>
              <Select.Option value="教育培训">教育培训</Select.Option>
              <Select.Option value="金融保险">金融保险</Select.Option>
              <Select.Option value="其他">其他</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="模板类型"
            name="type"
            rules={[{ required: true, message: '请选择模板类型' }]}
          >
            <Select placeholder="请选择模板类型">
              <Select.Option value="政府采购">政府采购</Select.Option>
              <Select.Option value="工程建设">工程建设</Select.Option>
              <Select.Option value="服务类">服务类</Select.Option>
              <Select.Option value="货物类">货物类</Select.Option>
              <Select.Option value="其他">其他</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="模板描述"
            name="description"
          >
            <Input.TextArea rows={4} placeholder="请输入模板描述，说明适用场景和特点" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">保存</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
export default TemplateList
