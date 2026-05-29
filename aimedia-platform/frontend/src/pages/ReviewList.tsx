import { Table, Tag, Button, Space } from 'antd'

export function ReviewList() {
  const data = [
    { id: '1', title: '冠心病的早期症状与预防', status: 'pending_1st', author: '张医生',
      submitted_at: '2025-05-01 10:30' },
  ]

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '作者', dataIndex: 'author', key: 'author', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color="processing">{s}</Tag> },
    { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', width: 160 },
    { title: '操作', key: 'action', width: 200,
      render: () => (
        <Space>
          <Button type="primary" size="small">通过</Button>
          <Button danger size="small">驳回</Button>
          <Button size="small">查看</Button>
        </Space>
      ),
    },
  ]

  return <Table columns={columns} dataSource={data} rowKey="id" />
}
