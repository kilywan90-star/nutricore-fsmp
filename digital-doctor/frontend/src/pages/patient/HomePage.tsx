import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Typography } from 'antd';
import {
  AlertOutlined, FileTextOutlined, MedicineBoxOutlined,
  LineChartOutlined, MessageOutlined,
} from '@ant-design/icons';

const { Title } = Typography;

const modules = [
  { title: '糖尿病风险评估', icon: <AlertOutlined />, path: '/patient/risk', desc: '基于ADA/中国指南的7因素评估' },
  { title: 'AI报告解读', icon: <FileTextOutlined />, path: '/patient/report', desc: '化验单拍照即得AI解读' },
  { title: '用药提醒', icon: <MedicineBoxOutlined />, path: '/patient/medication', desc: '智能用药计划+漏服提醒' },
  { title: '血糖记录', icon: <LineChartOutlined />, path: '/patient/glucose', desc: '记录+趋势+达标率分析' },
  { title: 'AI健康教练', icon: <MessageOutlined />, path: '/patient/coach', desc: '基于指南的个性化指导' },
];

export default function PatientHome() {
  const nav = useNavigate();
  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>数字医生分身</Title>
      <p style={{ color: '#666', marginBottom: 24 }}>内分泌科 · 您的AI健康管家</p>
      <Row gutter={[16, 16]}>
        {modules.map(m => (
          <Col xs={24} sm={12} key={m.path}>
            <Card hoverable onClick={() => nav(m.path)}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>{m.icon}</div>
              <Card.Meta title={m.title} description={m.desc} />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
