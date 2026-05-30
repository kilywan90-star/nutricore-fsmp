import { useEffect, useState } from 'react';
import {
  Card, Timeline, Typography, Tag, Button, Space, Badge, Collapse, Spin, Empty, message,
} from 'antd';
import {
  CheckCircleFilled, CloseCircleFilled, SafetyCertificateFilled, UserOutlined,
  ClockCircleOutlined, LinkOutlined, DisconnectOutlined, NumberOutlined,
  GlobalOutlined, ExpandOutlined,
} from '@ant-design/icons';
import {
  getAuditTrail,
  verifySignatureChain,
  type AuditTrailResponse,
  type ChainVerificationResponse,
  type AuditTrailItem,
} from '../lib/api';

const { Title, Text, Paragraph } = Typography;

interface Props {
  resourceType: string;
  resourceId: string;
}

const ACTION_LABELS: Record<string, string> = {
  confirmed: '确认采纳',
  approved: '审批通过',
  rejected: '驳回',
  acknowledged: '确认处理',
};

const ACTION_COLORS: Record<string, string> = {
  confirmed: 'green',
  approved: 'blue',
  rejected: 'red',
  acknowledged: 'orange',
};

export default function AuditTrailTimeline({ resourceType, resourceId }: Props) {
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [trail, setTrail] = useState<AuditTrailResponse | null>(null);
  const [chainResult, setChainResult] = useState<ChainVerificationResponse | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadTrail();
  }, [resourceType, resourceId]);

  const loadTrail = async () => {
    setLoading(true);
    try {
      const result = await getAuditTrail(resourceType, resourceId);
      setTrail(result);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '获取失败';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const result = await verifySignatureChain(resourceType, resourceId);
      setChainResult(result);
      if (result.valid) {
        message.success('签名链完整，数据未被篡改');
      } else {
        message.error('检测到链断裂或数据篡改');
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '验证失败';
      message.error(detail);
    } finally {
      setVerifying(false);
    }
  };

  const toggleExpand = (sigId: string) => {
    setExpandedId((prev) => (prev === sigId ? null : sigId));
  };

  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <Spin tip="加载签名链..." />
      </div>
    );
  }

  if (!trail || trail.signatures.length === 0) {
    return (
      <Card
        size="small"
        title={
          <Space>
            <SafetyCertificateFilled />
            <span>审计追踪</span>
          </Space>
        }
      >
        <Empty description="暂无签名记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  const sigs = trail.signatures;
  const chainVerifiedId = chainResult?.signatures.map((s) => s.signature_id) || [];

  return (
    <Card
      size="small"
      title={
        <Space>
          <SafetyCertificateFilled style={{ color: chainResult?.valid ? '#52c41a' : undefined }} />
          <span>审计追踪</span>
          {chainResult && (
            <Badge
              count={chainResult.valid ? '链完整' : '链断裂'}
              style={{
                backgroundColor: chainResult.valid ? '#52c41a' : '#ff4d4f',
              }}
            />
          )}
        </Space>
      }
      extra={
        <Button
          size="small"
          onClick={handleVerify}
          loading={verifying}
          icon={<SafetyCertificateFilled />}
        >
          验证链完整性
        </Button>
      }
    >
      <Timeline
        items={sigs.map((sig, idx) => {
          const verified = chainVerifiedId.includes(sig.id);
          const isExpanded = expandedId === sig.id;

          return {
            dot: (
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: chainResult
                    ? verified
                      ? '#f6ffed'
                      : '#fff2f0'
                    : '#f0f0f0',
                  border: `2px solid ${
                    chainResult ? (verified ? '#52c41a' : '#ff4d4f') : '#d9d9d9'
                  }`,
                }}
              >
                {chainResult ? (
                  verified ? (
                    <CheckCircleFilled style={{ color: '#52c41a', fontSize: 12 }} />
                  ) : (
                    <CloseCircleFilled style={{ color: '#ff4d4f', fontSize: 12 }} />
                  )
                ) : (
                  <NumberOutlined style={{ fontSize: 10, color: '#999' }} />
                )}
              </div>
            ),
            children: (
              <div>
                {/* Header */}
                <Space size="small" wrap>
                  <UserOutlined style={{ color: '#1677ff' }} />
                  <Text strong>{sig.user_id.slice(0, 8)}...</Text>
                  <Tag color={ACTION_COLORS[sig.action] || 'default'}>
                    {ACTION_LABELS[sig.action] || sig.action}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {new Date(sig.created_at).toLocaleString('zh-CN')}
                  </Text>
                </Space>

                {/* Link indicator */}
                <div style={{ marginTop: 4 }}>
                  {idx > 0 && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      <LinkOutlined style={{ marginRight: 4 }} />
                      前序签名: {(sig as AuditTrailItem & { previous_signature_id: string | null }).previous_signature_id
                        ? ((sig as AuditTrailItem & { previous_signature_id: string | null }).previous_signature_id!.slice(0, 8) + '...')
                        : '—'}
                    </Text>
                  )}
                </div>

                {/* Expand toggle */}
                <Button
                  type="link"
                  size="small"
                  icon={<ExpandOutlined />}
                  onClick={() => toggleExpand(sig.id)}
                  style={{ padding: 0, height: 'auto', marginTop: 4 }}
                >
                  {isExpanded ? '收起' : '详情'}
                </Button>

                {/* Expanded details */}
                {isExpanded && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: '8px 12px',
                      background: '#fafafa',
                      borderRadius: 4,
                      border: '1px solid #f0f0f0',
                    }}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        内容哈希:
                        <Paragraph code style={{ fontSize: 10, margin: '2px 0', wordBreak: 'break-all' }}>
                          {sig.content_hash}
                        </Paragraph>
                      </Text>
                      {sig.signature_data?.ip_address && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          <GlobalOutlined style={{ marginRight: 4 }} />
                          IP: {sig.signature_data.ip_address}
                        </Text>
                      )}
                      {sig.signature_data?.user_agent && (
                        <Text type="secondary" style={{ fontSize: 11, display: 'block', wordBreak: 'break-all' }}>
                          终端: {sig.signature_data.user_agent.slice(0, 80)}...
                        </Text>
                      )}
                    </Space>
                  </div>
                )}
              </div>
            ),
          };
        })}
      />

      {/* Broken links warning */}
      {chainResult && chainResult.broken_links.length > 0 && (
        <div
          style={{
            marginTop: 12,
            padding: '8px 12px',
            background: '#fff2f0',
            borderRadius: 4,
            border: '1px solid #ffccc7',
          }}
        >
          <Space>
            <DisconnectOutlined style={{ color: '#ff4d4f' }} />
            <Text type="danger" strong>链断裂详情:</Text>
          </Space>
          {chainResult.broken_links.map((link, idx) => (
            <div key={idx} style={{ marginTop: 4 }}>
              <Text type="danger" style={{ fontSize: 12 }}>{link}</Text>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
