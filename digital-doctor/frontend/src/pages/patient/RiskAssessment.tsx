import { Typography } from 'antd';

const { Title, Text } = Typography;

export default function RiskAssessment() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>糖尿病风险筛查</Title>
      <p>风险评估表单将在后续版本中实现，届时将提供基于中国人群风险评分的筛查工具。</p>
      <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
        * 本内容由AI生成，仅供临床参考，最终决策权归医生所有
      </Text>
    </div>
  );
}
