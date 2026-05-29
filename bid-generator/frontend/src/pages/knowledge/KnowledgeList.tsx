import React, { useState } from 'react'
import { Button, Card, Table, Tag, Space, Upload, message, Popconfirm } from 'antd'
import { PlusOutlined, UploadOutlined, DeleteOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
interface Knowledge {
  id: number
  name: string
  type: string
  category: string
  size: string
  upload_time: string
  status: 'indexed' | 'indexing' | 'failed'
}
const KnowledgeList: React.FC = () => {
  const [knowledges, setKnowledges] = useState<Knowledge[]>([
    {
      id: 1,
      name: '企业营业执照.pdf',
      type: 'pdf',
      category: '企业资质',
      size: '2.4MB',
      upload_time: '2024-05-01 10:00:00',
      status: 'indexed'
    },
    {
      id: 2,
      name: '2023年度财务审计报告.docx',
      type: 'docx',
      category: '财务资料',
      size: '3.8MB',
      upload_time: '2024-05-02 14:30:00',
      status: 'indexed'
    }
  ])
  const [loading, setLoading] = useState(false)
  const handleUpload = (file: any) => {
    // 后续对接上传API
    const newKnowledge: Knowledge = {
      id: knowledges.length > 0 ? Math.max(...knowledges.map(k => k.id)) + 1 : 1,
      name: file.name,
      type: file.name.split('.').pop()?.toLowerCase() || 'unknown',
      category: '其他',
      size: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
      upload_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      status: 'indexing'
    }
    setKnowledges([newKnowledge, ...knowledges])
    message.success(`${file.name} 上传成功，正在建立索引...`)
    // 模拟索引完成
    setTimeout(() => {
      setKnowledges(prev => prev.map(k =>
        k.id === newKnowledge.id ? { ...k, status: 'indexed' } : k
      ))
    }, 2000)
    return false // 阻止默认上传行为
  }
  const handleDelete = (id: number) => {
    setKnowledges(knowledges.filter(k => k.id !== id))
    message.success('删除成功')
  }
  const handlePreview = (record: Knowledge) => {
    // 后续实现预览功能
    message.info(`预览 ${record.name}`)
  }
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string, text: string }> = {
      indexed: { color: 'success', text: '已索引' },
      indexing: { color: 'processing', text: '索引中' },
      failed: { color: 'error', text: '索引失败' }
    }
    const info = statusMap[status] || { color: 'default', text: '未知' }
    return <Tag color={info.color}>{info.text}</Tag>
  }
  const getTypeTag = (type: string) => {
    const colorMap: Record<string, string> = {
      pdf: 'red',
      docx: 'blue',
      doc: 'blue',
      xlsx: 'green',
      xls: 'green',
      pptx: 'orange',
      ppt: 'orange'
    }
    return <Tag color={colorMap[type] || 'default'}>{type.toUpperCase()}</Tag>
  }
  const columns = [
    {
      title: '文件名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (type: string) => getTypeTag(type)
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      width: 100
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      width: 150,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm')
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: Knowledge) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          <Popconfirm
            title="确定要删除这个文件吗？"
            description="删除后文件和索引数据将无法恢复，请谨慎操作。"
            onConfirm={() => handleDelete(record.id)}
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
            <div className="page-title">知识库</div>
            <div className="page-subtitle">管理企业资质、过往标书、项目案例等资料，用于AI生成标书时检索引用</div>
          </div>
          <Upload
            fileList={[]}
            beforeUpload={handleUpload}
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt"
          >
            <Button type="primary" icon={<UploadOutlined />}>
              上传文件
            </Button>
          </Upload>
        </div>
      </div>
      <Card className="card-container">
        <Table
          columns={columns}
          dataSource={knowledges}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个文件`
          }}
        />
      </Card>
    </div>
  )
}
export default KnowledgeList
