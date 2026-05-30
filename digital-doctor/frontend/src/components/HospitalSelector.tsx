import { useEffect, useState } from 'react';
import { Select, Space, Tag, Typography } from 'antd';
import { BankOutlined } from '@ant-design/icons';
import { getHospitals, type HospitalItem } from '../lib/api';

const { Text } = Typography;

interface HospitalSelectorProps {
  value?: string;
  onChange?: (hospitalId: string) => void;
  showLabel?: boolean;
  style?: React.CSSProperties;
}

const levelColors: Record<string, string> = {
  '三级甲等': 'red',
  '三级乙等': 'orange',
  '二级甲等': 'blue',
  '二级乙等': 'cyan',
  '一级甲等': 'green',
};

export default function HospitalSelector({
  value,
  onChange,
  showLabel = true,
  style,
}: HospitalSelectorProps) {
  const [hospitals, setHospitals] = useState<HospitalItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await getHospitals();
        if (!cancelled) {
          setHospitals(data.items.filter((h) => h.is_active));
        }
      } catch {
        // Silently handle — user is likely not admin
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (hospitals.length === 0) return null;

  return (
    <Space>
      {showLabel && (
        <Text type="secondary">
          <BankOutlined style={{ marginRight: 4 }} />
          当前医院:
        </Text>
      )}
      <Select
        value={value}
        onChange={onChange}
        loading={loading}
        placeholder="选择医院"
        style={{ minWidth: 220, ...style }}
        options={hospitals.map((h) => ({
          value: h.id,
          label: (
            <Space>
              <span>{h.name}</span>
              {h.level && (
                <Tag color={levelColors[h.level] || 'default'} style={{ fontSize: 11 }}>
                  {h.level}
                </Tag>
              )}
            </Space>
          ),
        }))}
        allowClear
      />
    </Space>
  );
}
