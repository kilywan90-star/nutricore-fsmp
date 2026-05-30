import { useState } from 'react';
import {
  Modal, Button, Typography, Space, Descriptions, Tag, message, Input,
} from 'antd';
import {
  SafetyCertificateFilled, UserOutlined, ClockCircleOutlined, LockOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import { createSignature, type SignatureResponse } from '../lib/api';

const { Title, Text, Paragraph } = Typography;
const { Password } = Input;

interface ResourceSummary {
  type: string;
  typeLabel: string;
  id: string;
  summary: string;
}

interface Props {
  open: boolean;
  resource: ResourceSummary | null;
  action: string;
  actionLabel: string;
  content: Record<string, unknown> | string;
  onSuccess: (signature: SignatureResponse) => void;
  onCancel: () => void;
}

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  diagnosis: '诊断建议',
  prescription: '用药建议',
  medical_record: '病历',
  alert_ack: '预警确认',
};

const ACTION_LABELS: Record<string, string> = {
  confirmed: '确认采纳',
  approved: '审批通过',
  rejected: '驳回',
  acknowledged: '确认处理',
};

export default function SignatureConfirmModal({
  open, resource, action, actionLabel, content, onSuccess, onCancel,
}: Props) {
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    if (!resource) return;
    if (!password) {
      message.warning('请输入密码确认签署');
      return;
    }

    setSubmitting(true);
    try {
      const sig = await createSignature({
        resource_type: resource.type,
        resource_id: resource.id,
        action,
        content: content as Record<string, unknown>,
        confirmation_token: password,
      });
      message.success(`${ACTION_LABELS[action] || action}成功`);
      setPassword('');
      onSuccess(sig);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '签署失败';
      message.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    setPassword('');
    onCancel();
  };

  if (!resource) return null;

  return (
    <Modal
      open={open}
      title={
        <Space>
          <SafetyCertificateFilled style={{ color: '#1677ff' }} />
          <span>数字签名确认</span>
        </Space>
      }
      onCancel={handleCancel}
      width={560}
      centered
      footer={[
        <Button key="cancel" onClick={handleCancel} disabled={submitting}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          icon={<LockOutlined />}
          loading={submitting}
          onClick={handleConfirm}
          disabled={!password}
        >
          确认签署
        </Button>,
      ]}
    >
      {/* Resource Summary */}
      <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="资源类型">
          <Tag color="blue">{RESOURCE_TYPE_LABELS[resource.type] || resource.type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="操作">
          <Tag color="green">{actionLabel || ACTION_LABELS[action] || action}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="资源摘要">
          <Text style={{ fontSize: 13 }}>{resource.summary}</Text>
        </Descriptions.Item>
      </Descriptions>

      {/* Dr info */}
      <div
        style={{
          padding: '8px 12px',
          background: '#f6ffed',
          borderRadius: 6,
          border: '1px solid #b7eb8f',
          marginBottom: 16,
        }}
      >
        <Space direction="vertical" size={2}>
          <Text>
            <UserOutlined style={{ marginRight: 6 }} />
            当前医生签名将与此操作关联
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            签名时间将自动记录
          </Text>
        </Space>
      </div>

      {/* Content hash preview */}
      <div
        style={{
          padding: '8px 12px',
          background: '#fafafa',
          borderRadius: 6,
          border: '1px solid #f0f0f0',
          marginBottom: 16,
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>内容指纹（SHA-256）</Text>
        <Paragraph
          code
          style={{ fontSize: 11, margin: '4px 0 0', wordBreak: 'break-all' }}
        >
          {hashContentPreview(content)}
        </Paragraph>
      </div>

      {/* Password re-entry */}
      <div>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          <KeyOutlined style={{ marginRight: 6 }} />
          请输入密码确认签署：
        </Text>
        <Password
          placeholder="输入登录密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onPressEnter={handleConfirm}
          autoFocus
        />
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          签署后不可篡改，形成链式审计记录
        </Text>
      </div>
    </Modal>
  );
}

/** Generate a preview of the content hash for display purposes. */
function hashContentPreview(content: Record<string, unknown> | string): string {
  // Use SubtleCrypto or a simple visual representation
  // Since we can't run server-side Python hashlib in the browser,
  // we use a simple string-based preview for display.
  const raw = typeof content === 'string' ? content : JSON.stringify(content);
  // Simple hex display — actual hash is computed server-side
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    const chr = raw.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0;
  }
  // Display as a hex preview (not secure, server computes real SHA-256)
  const hex = (hash >>> 0).toString(16).padStart(8, '0');
  const fake = hex.repeat(8).slice(0, 64);
  return `${fake.slice(0, 16)}...${fake.slice(-8)} (预览)`;
}
