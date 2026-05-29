import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Select, Button, Card, Space, message } from 'antd'
import { contentApi } from '../services/api'

export function ContentEditor() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [aiGenLoading, setAiGenLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true)
    try {
      await contentApi.create(values)
      message.success('创建成功，已提交审核')
      navigate('/content')
    } catch {
      message.error('创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAIGenerate = async () => {
    const topic = form.getFieldValue('title')
    if (!topic) { message.warning('请先输入文章主题'); return }

    setAiGenLoading(true)
    try {
      const res = await fetch('/api/aigc/article', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, target_audience: '普通公众', word_count: 800 }),
      })
      const data = await res.json()
      form.setFieldValue('body', { text: data.content })
      form.setFieldValue('ai_generated', true)
      message.success('AI 生成完成，请检查并修改')
    } catch {
      message.error('AI 生成失败')
    } finally {
      setAiGenLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card title="新建内容">
        <Form form={form} layout="vertical" onFinish={onFinish}
              initialValues={{ content_type: 'article', ai_generated: false }}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input placeholder="输入文章主题..." />
          </Form.Item>
          <Form.Item name="content_type" label="内容类型">
            <Select options={[
              { value: 'article', label: '图文' },
              { value: 'video', label: '视频' },
              { value: 'image', label: '图片' },
            ]} />
          </Form.Item>
          <Form.Item name="body" label="正文" rules={[{ required: true }]}>
            <Input.TextArea rows={15} placeholder="输入正文或使用AI生成..." />
          </Form.Item>
          <Form.Item name="ai_generated" hidden><Input /></Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>保存并提交审核</Button>
              <Button onClick={handleAIGenerate} loading={aiGenLoading}>AI 生成正文</Button>
              <Button onClick={() => navigate('/content')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
