import { Typography } from 'antd';

const { Title } = Typography;

export default function GlucoseLog() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>血糖记录</Title>
      <p>血糖记录将在 Task 12 中实现</p>
    </div>
  );
}
