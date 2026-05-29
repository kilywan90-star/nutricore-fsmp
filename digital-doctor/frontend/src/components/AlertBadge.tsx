import React from 'react';
import { Tag } from 'antd';

interface AlertBadgeProps {
  severity: 'info' | 'warning' | 'critical';
  children?: React.ReactNode;
}

const severityConfig: Record<string, { color: string; label: string }> = {
  critical: { color: 'red', label: '危急' },
  warning: { color: 'orange', label: '预警' },
  info: { color: 'blue', label: '信息' },
};

const AlertBadge: React.FC<AlertBadgeProps> = ({ severity, children }) => {
  const config = severityConfig[severity] || severityConfig.info;
  return <Tag color={config.color}>{children || config.label}</Tag>;
};

export default AlertBadge;
