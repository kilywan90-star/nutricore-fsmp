import { Typography } from 'antd';

const { Title, Text } = Typography;

export default function HealthCoach() {
  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={3}>AI健康管理助手</Title>
      <p>健康管理助手将在后续版本中实现，届时将提供个性化生活方式建议和用药提醒。</p>
      <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
        * 本内容由AI生成，仅供临床参考，最终决策权归医生所有
      </Text>
    </div>
  );
}
