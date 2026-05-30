import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { List, Card, Typography, Badge, Spin, Empty, Tag } from 'antd';
import { HeartOutlined } from '@ant-design/icons';
import { getGrassrootsPatients, type GrassrootsPatientItem } from '../../lib/api';

const { Title, Text } = Typography;

export default function FollowUpList() {
  const nav = useNavigate();
  const [patients, setPatients] = useState<GrassrootsPatientItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const data = await getGrassrootsPatients();
      setPatients(data);
    } catch {
      // offline
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  if (!patients.length) {
    return <Empty description="暂无患者数据" style={{ marginTop: 80 }} />;
  }

  const overduePatients = patients.filter((p) => {
    if (!p.last_follow_up) return true;
    return true; // All patients appear; overdue indication via tag
  });

  const riskColor: Record<string, string> = {
    high: '#ff4d4f',
    very_high: '#ff4d4f',
    moderate: '#faad14',
    low: '#52c41a',
    unknown: '#999',
  };

  const riskLabel: Record<string, string> = {
    high: '高危',
    very_high: '极高危',
    moderate: '中危',
    low: '低危',
    unknown: '未知',
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <HeartOutlined /> 随访列表
      </Title>
      <List
        dataSource={patients}
        renderItem={(item: GrassrootsPatientItem) => (
          <Card
            size="small"
            style={{ marginBottom: 8, cursor: 'pointer' }}
            onClick={() => nav(`/grassroots/follow-up/${item.id}`)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text strong style={{ fontSize: 16 }}>{item.name}</Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>{item.gender} {item.age}岁</Text>
              </div>
              <Tag color={riskColor[item.risk_status || 'unknown']}>
                {riskLabel[item.risk_status || 'unknown']}
              </Tag>
            </div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#999' }}>
              {item.village} | 最近血糖：{item.latest_fpg != null ? `${item.latest_fpg} mmol/L` : '暂无'}
            </div>
            {item.last_follow_up && (
              <div style={{ fontSize: 12, color: '#bbb', marginTop: 2 }}>
                上次随访：{new Date(item.last_follow_up).toLocaleDateString('zh-CN')}
              </div>
            )}
          </Card>
        )}
      />
    </div>
  );
}
