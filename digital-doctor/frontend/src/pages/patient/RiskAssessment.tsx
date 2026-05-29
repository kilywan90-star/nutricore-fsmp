import { Typography } from 'antd';

const { Title } = Typography;

export default function RiskAssessment() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>糖尿病风险评估</Title>
      <p>评估表单将在 Task 11 中实现</p>
    </div>
  );
}
