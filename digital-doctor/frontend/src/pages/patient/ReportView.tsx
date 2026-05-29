import { Typography } from 'antd';

const { Title } = Typography;

export default function ReportView() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>AI报告解读</Title>
      <p>报告解读将在 Task 11 中实现</p>
    </div>
  );
}
