import { Card, Typography } from 'antd';
import { useParams } from 'react-router-dom';

export default function PatientDetail() {
  const { id } = useParams();
  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Typography.Title level={3}>患者详情</Typography.Title>
      <Card><p>患者 {id} 详情 — 待实现</p></Card>
    </div>
  );
}
