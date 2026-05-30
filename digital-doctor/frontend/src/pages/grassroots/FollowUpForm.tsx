import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Switch, Checkbox, Card, Typography, message, DatePicker } from 'antd';
import dayjs from 'dayjs';
import { recordFollowUp } from '../../lib/api';

const { Title } = Typography;
const { TextArea } = Input;

export default function FollowUpForm() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: any) => {
    if (!id) return;
    setSubmitting(true);
    try {
      await recordFollowUp(id, {
        glucose_value: values.glucose_value || undefined,
        medication_adherent: values.medication_adherent,
        new_symptoms: values.new_symptoms || undefined,
        referral_needed: values.referral_needed || false,
        referral_reason: values.referral_reason || undefined,
        notes: values.notes || undefined,
        next_follow_up: values.next_follow_up
          ? values.next_follow_up.format('YYYY-MM-DD')
          : undefined,
      });
      message.success('随访记录已保存');
      nav('/grassroots/follow-up');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>随访记录</Title>
      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit} size="large">
          <Form.Item name="glucose_value" label="血糖值 (mmol/L)">
            <Input type="number" min={1} max={40} step={0.1} placeholder="如：7.2" />
          </Form.Item>

          <Form.Item name="medication_adherent" label="是否规律服药" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>

          <Form.Item name="new_symptoms" label="新发症状">
            <TextArea rows={3} placeholder="如：多饮、多尿、视物模糊..." maxLength={500} />
          </Form.Item>

          <Form.Item name="referral_needed" label="是否需要转诊" valuePropName="checked">
            <Checkbox>需要转诊至上级医院</Checkbox>
          </Form.Item>

          <Form.Item name="referral_reason" label="转诊原因">
            <TextArea rows={2} placeholder="简要说明转诊原因..." maxLength={500} />
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <TextArea rows={2} placeholder="其他备注..." maxLength={500} />
          </Form.Item>

          <Form.Item name="next_follow_up" label="下次随访日期">
            <DatePicker style={{ width: '100%' }} placeholder="选择日期" />
          </Form.Item>

          <Form.Item style={{ marginTop: 16 }}>
            <Button type="primary" htmlType="submit" block size="large" loading={submitting} style={{ height: 50 }}>
              保存随访
            </Button>
          </Form.Item>
          <Button block size="large" onClick={() => nav('/grassroots/follow-up')}>
            返回列表
          </Button>
        </Form>
      </Card>
    </div>
  );
}
