import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Modal, Button, Typography, Tag, Space, Descriptions, message, Radio, Input,
} from 'antd';
import {
  WarningFilled, ClockCircleFilled, CheckCircleFilled, PhoneFilled, AlertFilled,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

export interface CriticalAlertData {
  id: string;
  patient_id: string;
  alert_type: string;
  severity: string;
  title: string;
  detail: string;
  value: number;
  detected_at: string;
  doctor_user_id: string | null;
  status: string;
  acknowledged_at: string | null;
  resolution: string | null;
}

interface Props {
  alert: CriticalAlertData | null;
  onAcknowledge: (alertId: string, resolution: string, notes?: string) => Promise<void>;
  onClose: () => void;
}

const ACK_TIMEOUT_SECONDS = 30 * 60; // 30 minutes
const WARNING_THRESHOLD = 5 * 60; // flash red at 5 min remaining

const ALERT_TYPE_LABELS: Record<string, string> = {
  severe_hyperglycemia: '严重高血糖',
  hypoglycemia: '低血糖',
};

export default function CriticalAlertModal({ alert, onAcknowledge, onClose }: Props) {
  const [resolution, setResolution] = useState<string>('已处理');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number>(ACK_TIMEOUT_SECONDS);
  const [countdownStarted, setCountdownStarted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start countdown when alert appears
  useEffect(() => {
    if (alert && !countdownStarted) {
      setCountdownStarted(true);
      setTimeLeft(ACK_TIMEOUT_SECONDS);
      setResolution('已处理');
      setNotes('');
    }
    if (!alert) {
      setCountdownStarted(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setTimeLeft(ACK_TIMEOUT_SECONDS);
    }
  }, [alert, countdownStarted]);

  // Countdown timer
  useEffect(() => {
    if (!alert || !countdownStarted) return;

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [alert, countdownStarted]);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const isWarning = timeLeft <= WARNING_THRESHOLD;
  const isExpired = timeLeft <= 0;

  const handleConfirm = async () => {
    if (!alert) return;
    setSubmitting(true);
    try {
      await onAcknowledge(alert.id, resolution, notes);
      message.success('预警已处理');
      setCountdownStarted(false);
      onClose();
    } catch (err: any) {
      message.error(err?.message || '处理失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (!alert) return null;

  const alertLabel = ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type;

  return (
    <Modal
      open
      closable={false}
      maskClosable={false}
      footer={null}
      width={640}
      centered
      style={{ top: 20 }}
      styles={{
        body: { padding: 32 },
      }}
    >
      {/* ── Header ── */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <WarningFilled
          style={{
            fontSize: 48,
            color: isWarning ? '#ff4d4f' : '#faad14',
            animation: isWarning ? 'pulse 1s infinite' : 'none',
          }}
        />
        <Title level={3} style={{ margin: '12px 0 4px', color: '#cf1322' }}>
          危急值预警
        </Title>
        <Tag color="red" style={{ fontSize: 14, padding: '2px 12px' }}>
          {alertLabel}
        </Tag>
      </div>

      {/* ── Timer ── */}
      <div
        style={{
          textAlign: 'center',
          marginBottom: 20,
          padding: '12px 0',
          background: isWarning ? '#fff2f0' : isExpired ? '#fff1f0' : '#f6ffed',
          borderRadius: 8,
          border: `2px solid ${isWarning || isExpired ? '#ff4d4f' : '#b7eb8f'}`,
        }}
      >
        <ClockCircleFilled
          style={{
            fontSize: 18,
            color: isWarning || isExpired ? '#ff4d4f' : '#52c41a',
            animation: isWarning ? 'pulse 0.5s infinite' : 'none',
          }}
        />
        <Text
          strong
          style={{
            fontSize: 24,
            marginLeft: 8,
            fontFamily: 'monospace',
            color: isWarning || isExpired ? '#ff4d4f' : '#52c41a',
          }}
        >
          {formatTime(timeLeft)}
        </Text>
        {(isWarning || isExpired) && (
          <div style={{ marginTop: 4 }}>
            <Text type="danger" strong>
              {isExpired ? '超时！将自动升级至科室负责人' : '即将超时，请尽快处理！'}
            </Text>
          </div>
        )}
      </div>

      {/* ── Alert Details ── */}
      <Descriptions
        bordered
        size="small"
        column={1}
        style={{ marginBottom: 20 }}
        labelStyle={{ width: 100, fontWeight: 600 }}
      >
        <Descriptions.Item label="患者ID">
          {alert.patient_id.slice(0, 8)}...
        </Descriptions.Item>
        <Descriptions.Item label="血糖值">
          <Text strong style={{ color: '#cf1322', fontSize: 18 }}>
            {alert.value} mmol/L
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="详情">{alert.detail}</Descriptions.Item>
        <Descriptions.Item label="检测时间">
          {new Date(alert.detected_at).toLocaleString('zh-CN')}
        </Descriptions.Item>
        <Descriptions.Item label="当前状态">
          <Tag color="red">{alert.status}</Tag>
        </Descriptions.Item>
      </Descriptions>

      {/* ── Resolution Actions ── */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          处理方式：
        </Text>
        <Radio.Group
          value={resolution}
          onChange={(e) => setResolution(e.target.value)}
          buttonStyle="solid"
          size="large"
          style={{ width: '100%', display: 'flex', gap: 8 }}
        >
          <Radio.Button
            value="已处理"
            style={{ flex: 1, textAlign: 'center', height: 48, lineHeight: '48px' }}
          >
            <CheckCircleFilled style={{ color: '#52c41a', marginRight: 4 }} />
            已处理
          </Radio.Button>
          <Radio.Button
            value="已联系患者"
            style={{ flex: 1, textAlign: 'center', height: 48, lineHeight: '48px' }}
          >
            <PhoneFilled style={{ color: '#1677ff', marginRight: 4 }} />
            已联系患者
          </Radio.Button>
          <Radio.Button
            value="转急诊"
            style={{ flex: 1, textAlign: 'center', height: 48, lineHeight: '48px' }}
          >
            <AlertFilled style={{ color: '#ff4d4f', marginRight: 4 }} />
            转急诊
          </Radio.Button>
        </Radio.Group>
      </div>

      {/* ── Notes ── */}
      <div style={{ marginBottom: 20 }}>
        <TextArea
          rows={2}
          placeholder="处理备注（选填）"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={200}
          showCount
        />
      </div>

      {/* ── Confirm Button ── */}
      <Button
        type="primary"
        danger={resolution === '转急诊'}
        block
        size="large"
        loading={submitting}
        onClick={handleConfirm}
        disabled={isExpired}
        style={{ height: 48, fontSize: 16 }}
      >
        确认处理
      </Button>

      {isExpired && (
        <Text type="danger" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
          该预警已超时并自动升级
        </Text>
      )}

      {/* CSS animation for pulse effect */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </Modal>
  );
}
