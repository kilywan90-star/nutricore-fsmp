import { useEffect, useState } from 'react';
import { Card, Typography, Spin, Empty, Tag, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { getGrassrootsPatients, type GrassrootsPatientItem } from '../../lib/api';

const { Title, Text } = Typography;

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

export default function PatientCards() {
  const [patients, setPatients] = useState<GrassrootsPatientItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

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

  const filtered = patients.filter(
    (p) =>
      !search ||
      p.name.includes(search) ||
      p.village.includes(search),
  );

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>患者管理</Title>

      <Input.Search
        placeholder="搜索姓名或村名..."
        allowClear
        onSearch={setSearch}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 16 }}
        prefix={<SearchOutlined />}
      />

      {!filtered.length ? (
        <Empty description="暂无患者数据" />
      ) : (
        filtered.map((p) => (
          <Card key={p.id} size="small" style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Text strong style={{ fontSize: 16 }}>{p.name}</Text>
                  <Text type="secondary">{p.gender} {p.age}岁</Text>
                </div>
                <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>
                  {p.village} | {p.diabetes_type || '未确诊'}
                </div>
                <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>最近血糖</Text>
                    <div style={{ fontSize: 14 }}>
                      {p.latest_fpg != null ? (
                        <span style={{ color: p.latest_fpg >= 7.0 ? '#ff4d4f' : '#52c41a' }}>
                          {p.latest_fpg} mmol/L
                        </span>
                      ) : (
                        <span style={{ color: '#999' }}>-</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>上次随访</Text>
                    <div style={{ fontSize: 14, color: '#666' }}>
                      {p.last_follow_up
                        ? new Date(p.last_follow_up).toLocaleDateString('zh-CN')
                        : '暂无'}
                    </div>
                  </div>
                </div>
              </div>
              <Tag color={riskColor[p.risk_status || 'unknown']} style={{ marginTop: 0 }}>
                {riskLabel[p.risk_status || 'unknown']}
              </Tag>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
