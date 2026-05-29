import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Typography, Button, Input, List, Tag, Space, Alert, Empty, Avatar, Divider,
} from 'antd';
import {
  ArrowLeftOutlined, MessageOutlined, UserOutlined, RobotOutlined,
  WarningOutlined, SendOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { chatWithCoach, type CoachReply } from '../../lib/api';
import { mockCoachReply } from '../../lib/mock';

const { Title, Text, Paragraph } = Typography;

interface ChatMessage {
  id: string;
  role: 'user' | 'coach';
  text: string;
  isUrgent?: boolean;
  timestamp: string;
}

const URGENT_KEYWORDS = [
  '心慌', '出冷汗', '头晕', '看不清', '昏迷', '晕倒', '测不出',
  '很高', '低血糖', '发抖', '面色苍白', '胸闷',
];

function hasUrgentKeywords(text: string): boolean {
  return URGENT_KEYWORDS.some(kw => text.includes(kw));
}

export default function HealthCoach() {
  const nav = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'system-1',
      role: 'coach',
      text: '您好！我是您的AI健康教练，基于《中国2型糖尿病防治指南(2024版)》为您提供个性化的日常管理建议。请告诉我您的情况或问题，我会尽力帮助您。\n\n提醒：AI建议不能替代医生诊断。如出现严重高血糖、低血糖或急性并发症症状，请立即就医。',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [showUrgentWarning, setShowUrgentWarning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const text = inputValue.trim();
    if (!text) return;

    const isUrgent = hasUrgentKeywords(text);
    if (isUrgent) setShowUrgentWarning(true);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
      isUrgent,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);

    let reply: CoachReply;
    try {
      reply = await chatWithCoach({ message: text });
    } catch {
      reply = mockCoachReply(text);
    }

    const coachMsg: ChatMessage = {
      id: `coach-${Date.now()}`,
      role: 'coach',
      text: reply.reply,
      isUrgent: reply.is_urgent,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, coachMsg]);
    setLoading(false);

    if (reply.is_urgent) setShowUrgentWarning(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 700, margin: '0 auto', height: 'calc(100vh - 48px)', display: 'flex', flexDirection: 'column' }}>
      <Button icon={<ArrowLeftOutlined />} type="link" onClick={() => nav('/patient')} style={{ padding: 0, marginBottom: 8 }}>
        返回首页
      </Button>

      <Title level={3} style={{ marginBottom: 8 }}><MessageOutlined /> AI健康教练</Title>

      <Alert
        message="基于《中国2型糖尿病防治指南(2024版)》"
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 12 }}
        closable
      />

      {showUrgentWarning && (
        <Alert
          message="紧急提醒"
          description="检测到紧急关键词。AI教练无法替代急诊医疗。如出现严重低血糖（<3.9mmol/L）、严重高血糖（>16.7mmol/L）、或胸痛、呼吸困难、意识模糊等症状，请立即测量血糖并拨打120或前往急诊。"
          type="error"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 12 }}
          closable
          onClose={() => setShowUrgentWarning(false)}
        />
      )}

      <Card
        size="small"
        style={{ flex: 1, marginBottom: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'auto', padding: 12 }}
      >
        <div style={{ flex: 1, overflow: 'auto' }}>
          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 12,
              }}
            >
              {msg.role === 'coach' && (
                <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1677ff', marginRight: 8, flexShrink: 0 }} />
              )}
              <div style={{ maxWidth: '80%' }}>
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 12,
                    backgroundColor: msg.role === 'user' ? '#1677ff' : '#f0f2f5',
                    color: msg.role === 'user' ? '#fff' : '#000',
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                    border: msg.isUrgent ? '2px solid #ff4d4f' : undefined,
                  }}
                >
                  {msg.text}
                </div>
                <div style={{
                  fontSize: 11,
                  color: '#999',
                  marginTop: 4,
                  textAlign: msg.role === 'user' ? 'right' : 'left',
                  padding: '0 4px',
                }}>
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  {msg.isUrgent && (
                    <Tag color="red" style={{ marginLeft: 4, fontSize: 10 }}>紧急</Tag>
                  )}
                </div>
              </div>
              {msg.role === 'user' && (
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#52c41a', marginLeft: 8, flexShrink: 0 }} />
              )}
            </div>
          ))}
          {loading && (
            <div style={{ textAlign: 'left', padding: 8 }}>
              <Text type="secondary">AI教练正在思考...</Text>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </Card>

      <div style={{ display: 'flex', gap: 8 }}>
        <Input.TextArea
          ref={inputRef}
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="向AI健康教练提问..."
          autoSize={{ minRows: 1, maxRows: 3 }}
          style={{ flex: 1 }}
          disabled={loading}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={sendMessage}
          loading={loading}
          disabled={!inputValue.trim()}
          style={{ alignSelf: 'flex-end' }}
        >
          发送
        </Button>
      </div>
    </div>
  );
}
