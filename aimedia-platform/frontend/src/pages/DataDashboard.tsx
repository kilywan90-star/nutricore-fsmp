import { Card, Col, Row, Statistic } from 'antd'
import { EyeOutlined, LikeOutlined, MessageOutlined, ShareAltOutlined } from '@ant-design/icons'

export function DataDashboard() {
  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card><Statistic title="总阅读量" value={128300} prefix={<EyeOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总点赞" value={8920} prefix={<LikeOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总评论" value={1542} prefix={<MessageOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总转发" value={3210} prefix={<ShareAltOutlined />} /></Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="传播力排名">传播力排名图表（待对接数据源）</Card>
        </Col>
        <Col span={12}>
          <Card title="渠道分布">渠道分布图表（待对接数据源）</Card>
        </Col>
      </Row>
    </div>
  )
}
