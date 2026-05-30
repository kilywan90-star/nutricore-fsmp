import { Typography } from 'antd';

const { Title, Text } = Typography;

export default function ReportView() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>AI辅助报告解读</Title>
      <p>报告解读功能将在后续版本中实现，届时将提供化验结果辅助解读。</p>
      <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
        * 本内容由AI生成，仅供临床参考，最终决策权归医生所有
      </Text>
    </div>
  );
}
