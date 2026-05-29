import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Typography, Button, List, Tag, Badge, Switch, Space, Empty, Timeline, Checkbox,
} from 'antd';
import {
  ArrowLeftOutlined, MedicineBoxOutlined, ClockCircleOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { mockMedications, type MedicationItem } from '../../lib/mock';

const { Title, Text } = Typography;

interface DoseStatus {
  [medicationId: string]: Set<string>;
}

function getFrequencyLabel(freq: string): string {
  const map: Record<string, string> = { qd: '每日1次', bid: '每日2次', tid: '每日3次', qid: '每日4次' };
  return map[freq] || freq;
}

export default function MedicationPage() {
  const nav = useNavigate();
  const [medications] = useState<MedicationItem[]>(mockMedications());
  const [takenDoses, setTakenDoses] = useState<DoseStatus>({});

  const toggleDose = (medicationId: string, time: string) => {
    setTakenDoses(prev => {
      const next = { ...prev };
      if (!next[medicationId]) next[medicationId] = new Set();
      const doses = new Set(next[medicationId]);
      if (doses.has(time)) {
        doses.delete(time);
      } else {
        doses.add(time);
      }
      next[medicationId] = doses;
      return next;
    });
  };

  const allDoses = useMemo(() => {
    const result: Array<{ medicationId: string; drugName: string; dosage: string; time: string }> = [];
    medications.forEach(m => {
      if (!m.is_active) return;
      m.time_of_day.forEach(t => {
        result.push({ medicationId: m.id, drugName: m.drug_name, dosage: m.dosage, time: t });
      });
    });
    result.sort((a, b) => a.time.localeCompare(b.time));
    return result;
  }, [medications]);

  const takenCount = Object.values(takenDoses).reduce((sum, s) => sum + s.size, 0);
  const totalCount = allDoses.length;
  const adherenceRate = totalCount > 0 ? Math.round((takenCount / totalCount) * 100) : 0;

  const timelineItems = allDoses.map(dose => {
    const isTaken = takenDoses[dose.medicationId]?.has(dose.time);
    return {
      color: isTaken ? 'green' : 'blue',
      dot: isTaken ? <CheckCircleOutlined /> : <ClockCircleOutlined />,
      children: (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Text strong style={{ marginRight: 8 }}>{dose.time}</Text>
            <Text>{dose.drugName}</Text>
            <Tag color="blue" style={{ marginLeft: 8 }}>{dose.dosage}</Tag>
          </div>
          <Checkbox
            checked={isTaken}
            onChange={() => toggleDose(dose.medicationId, dose.time)}
          />
        </div>
      ),
    };
  });

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Button icon={<ArrowLeftOutlined />} type="link" onClick={() => nav('/patient')} style={{ padding: 0, marginBottom: 16 }}>
        返回首页
      </Button>

      <Title level={3}><MedicineBoxOutlined /> 用药提醒</Title>

      <Card size="small" style={{ marginBottom: 16, background: '#f0f5ff' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text>今日用药依从性</Text>
          <Text strong style={{ fontSize: 18, color: adherenceRate >= 80 ? '#52c41a' : '#faad14' }}>
            {adherenceRate}% ({takenCount}/{totalCount})
          </Text>
        </Space>
        <div style={{
          height: 8, background: '#f0f0f0', borderRadius: 4, marginTop: 8, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: `${adherenceRate}%`, background: adherenceRate >= 80 ? '#52c41a' : '#faad14',
            borderRadius: 4, transition: 'width 0.3s',
          }} />
        </div>
      </Card>

      {medications.length === 0 ? (
        <Empty description="暂无用药计划" />
      ) : (
        <Card title="药品列表" style={{ marginBottom: 16 }}>
          <List
            dataSource={medications}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  title={<Text strong>{item.drug_name} <Tag>{item.dosage}</Tag></Text>}
                  description={
                    <Space>
                      <Text type="secondary">{getFrequencyLabel(item.frequency)}</Text>
                      <Text type="secondary">{item.time_of_day.join(', ')}</Text>
                      {!item.is_active && <Tag color="red">已停用</Tag>}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card title={`今日用药时间线 (${takenCount}/${totalCount} 已完成)`}>
        {allDoses.length === 0 ? (
          <Empty description="今日无用药安排" />
        ) : (
          <Timeline items={timelineItems} />
        )}
      </Card>
    </div>
  );
}
