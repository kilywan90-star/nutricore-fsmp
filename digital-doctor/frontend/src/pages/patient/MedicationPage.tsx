import { Typography } from 'antd';

const { Title } = Typography;

export default function MedicationPage() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>用药提醒</Title>
      <p>用药提醒将在 Task 12 中实现</p>
    </div>
  );
}
