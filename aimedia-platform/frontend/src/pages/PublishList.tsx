import { Table, Tag, Button, Space } from 'antd'

export function PublishList() {
  const data = [
    { id: '1', title: '冠心病的早期症状与预防', channels: ['微信公众号', '抖音'], status: 'success',
      published_at: '2025-05-02 09:00' },
  ]

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '渠道', dataIndex: 'channels', key: 'channels',
      render: (chs: string[]) => chs.map(c => <Tag key={c}>{c}</Tag>) },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={s === 'success' ? 'success' : 'default'}>{s}</Tag> },
    { title: '发布时间', dataIndex: 'published_at', key: 'published_at', width: 160 },
    { title: '操作', key: 'action', width: 160,
      render: () => (
        <Space>
          <Button size="small">查看数据</Button>
          <Button size="small" danger>撤回</Button>
        </Space>
      ),
    },
  ]

  return <Table columns={columns} dataSource={data} rowKey="id" />
}
