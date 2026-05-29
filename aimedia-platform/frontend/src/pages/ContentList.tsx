import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Tag, Space, Input } from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  pending_1st: { color: 'processing', label: '一审中' },
  pending_2nd: { color: 'processing', label: '二审中' },
  pending_3rd: { color: 'processing', label: '三审中' },
  approved: { color: 'success', label: '已通过' },
  published: { color: 'blue', label: '已发布' },
  offline: { color: 'warning', label: '已下架' },
}

export function ContentList() {
  const navigate = useNavigate()
  const [data] = useState([
    { id: '1', title: '冠心病的早期症状与预防', status: 'published', content_type: 'article',
      created_at: '2025-05-01T10:00:00Z' },
    { id: '2', title: '膝关节置换术后康复指南', status: 'pending_1st', content_type: 'video',
      created_at: '2025-05-02T14:30:00Z' },
  ])

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', width: 300 },
    { title: '类型', dataIndex: 'content_type', key: 'content_type', width: 80,
      render: (t: string) => t === 'article' ? '图文' : t === 'video' ? '视频' : t },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => {
        const cfg = STATUS_MAP[s] || { color: 'default', label: s }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: unknown, record: { id: string }) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/content/${record.id}/edit`)}>编辑</Button>
          <Button type="link" size="small">审核</Button>
          <Button type="link" size="small">发布</Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input prefix={<SearchOutlined />} placeholder="搜索内容..." style={{ width: 300 }} />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/content/new')}>
          新建内容
        </Button>
      </div>
      <Table columns={columns} dataSource={data} rowKey="id" />
    </div>
  )
}
