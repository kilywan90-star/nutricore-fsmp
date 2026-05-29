import React, { useState, useEffect } from 'react'
import { Button, Card, Table, Tag, Space, Modal, Form, Input, Select, DatePicker, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, EyeOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'
const { Option } = Select
const { RangePicker } = DatePicker
interface Project {
  id: number
  name: string
  type: string
  industry: string
  description: string
  deadline: string
  status: 'draft' | 'generating' | 'completed' | 'archived'
  created_at: string
  updated_at: string
}
const ProjectList: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  // 模拟项目数据，后续换成接口调用
  useEffect(() => {
    loadProjects()
  }, [])
  const loadProjects = async () => {
    setLoading(true)
    try {
      // 模拟数据，后续对接API
      const mockProjects: Project[] = [
        {
          id: 1,
          name: 'XX政府智慧园区建设项目投标',
          type: '政府采购',
          industry: 'IT/互联网',
          description: '智慧园区信息化建设项目，包含平台开发、硬件部署等',
          deadline: '2024-06-30',
          status: 'draft',
          created_at: '2024-05-01 10:00:00',
          updated_at: '2024-05-05 14:30:00'
        },
        {
          id: 2,
          name: 'XX建筑工程有限公司办公楼装修项目',
          type: '工程建设',
          industry: '建筑工程',
          description: '办公楼室内外装修工程，总面积5000平米',
          deadline: '2024-07-15',
          status: 'completed',
          created_at: '2024-04-20 09:15:00',
          updated_at: '2024-04-28 16:20:00'
        }
      ]
      setProjects(mockProjects)
    } catch (error) {
      message.error('加载项目列表失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }
  const handleCreateProject = () => {
    setEditingProject(null)
    form.resetFields()
    setModalVisible(true)
  }
  const handleEditProject = (project: Project) => {
    setEditingProject(project)
    form.setFieldsValue({
      ...project,
      deadline: dayjs(project.deadline)
    })
    setModalVisible(true)
  }
  const handleDeleteProject = async (id: number) => {
    try {
      // 后续对接删除API
      setProjects(projects.filter(p => p.id !== id))
      message.success('删除成功')
    } catch (error) {
      message.error('删除失败')
      console.error(error)
    }
  }
  const handleSubmitProject = async (values: any) => {
    try {
      const projectData = {
        ...values,
        deadline: values.deadline?.format('YYYY-MM-DD')
      }
      if (editingProject) {
        // 编辑项目，后续对接API
        setProjects(projects.map(p => p.id === editingProject.id ? { ...p, ...projectData } : p))
        message.success('项目更新成功')
      } else {
        // 新建项目，后续对接API
        const newProject: Project = {
          id: projects.length > 0 ? Math.max(...projects.map(p => p.id)) + 1 : 1,
          ...projectData,
          status: 'draft',
          created_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
          updated_at: dayjs().format('YYYY-MM-DD HH:mm:ss')
        }
        setProjects([newProject, ...projects])
        message.success('项目创建成功')
      }
      setModalVisible(false)
    } catch (error) {
      message.error('保存失败')
      console.error(error)
    }
  }
  const handleGenerateBid = (id: number) => {
    navigate(`/editor/${id}`)
  }
  const handleViewProject = (id: number) => {
    navigate(`/editor/${id}`)
  }
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string, text: string }> = {
      draft: { color: 'default', text: '草稿' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      archived: { color: 'warning', text: '已归档' }
    }
    const info = statusMap[status] || { color: 'default', text: '未知' }
    return <Tag color={info.color}>{info.text}</Tag>
  }
  const columns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      width: 280,
      ellipsis: true
    },
    {
      title: '项目类型',
      dataIndex: 'type',
      key: 'type',
      width: 120
    },
    {
      title: '所属行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 120
    },
    {
      title: '投标截止日期',
      dataIndex: 'deadline',
      key: 'deadline',
      width: 120,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD')
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm')
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
      width: 200,
      render: (_: any, record: Project) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleGenerateBid(record.id)}
          >
            生成标书
          </Button>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewProject(record.id)}
          >
            查看
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditProject(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个项目吗？"
            description="删除后项目数据将无法恢复，请谨慎操作。"
            onConfirm={() => handleDeleteProject(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
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
            <div className="page-title">项目管理</div>
            <div className="page-subtitle">管理所有投标项目，创建、编辑或生成标书</div>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateProject}>
            新建项目
          </Button>
        </div>
      </div>
      <Card className="card-container">
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个项目`
          }}
        />
      </Card>
      <Modal
        title={editingProject ? '编辑项目' : '新建项目'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmitProject}
        >
          <Form.Item
            label="项目名称"
            name="name"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item
            label="项目类型"
            name="type"
            rules={[{ required: true, message: '请选择项目类型' }]}
          >
            <Select placeholder="请选择项目类型">
              <Option value="政府采购">政府采购</Option>
              <Option value="工程建设">工程建设</Option>
              <Option value="服务类">服务类</Option>
              <Option value="货物类">货物类</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="所属行业"
            name="industry"
            rules={[{ required: true, message: '请选择所属行业' }]}
          >
            <Select placeholder="请选择所属行业">
              <Option value="IT/互联网">IT/互联网</Option>
              <Option value="建筑工程">建筑工程</Option>
              <Option value="医疗健康">医疗健康</Option>
              <Option value="教育培训">教育培训</Option>
              <Option value="金融保险">金融保险</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="投标截止日期"
            name="deadline"
            rules={[{ required: true, message: '请选择投标截止日期' }]}
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择投标截止日期" />
          </Form.Item>
          <Form.Item
            label="项目描述"
            name="description"
          >
            <Input.TextArea rows={4} placeholder="请输入项目描述（可选）" />
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
export default ProjectList
