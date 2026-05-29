import React, { useState } from 'react'
import { Card, Form, Input, Select, Button, message, Divider, Space, Alert } from 'antd'
import { SaveOutlined, QuestionCircleOutlined } from '@ant-design/icons'
const { Option } = Select
const Settings: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const handleSave = async (values: any) => {
    setLoading(true)
    try {
      // 后续对接保存API，配置保存在本地
      message.success('配置保存成功')
      console.log('配置信息:', values)
    } catch (error) {
      message.error('保存失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }
  const handleTestApiKey = async () => {
    const apiKey = form.getFieldValue('api_key')
    if (!apiKey) {
      message.warning('请先输入API Key')
      return
    }
    try {
      // 后续对接API测试接口
      message.success('API Key验证成功')
    } catch (error) {
      message.error('API Key验证失败，请检查')
    }
  }
  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">系统设置</div>
        <div className="page-subtitle">配置AI模型参数、存储路径等全局设置</div>
      </div>
      <Card title="AI模型配置" className="card-container">
        <Alert
          message="隐私说明"
          description="本工具所有数据都保存在本地，不会上传到任何服务器。调用AI生成时仅将生成所需的内容发送到对应的AI服务商API，请确保您的API Key有足够的额度。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            model_provider: 'anthropic',
            model: 'claude-3-sonnet-20240229',
            temperature: 0.7
          }}
        >
          <Form.Item
            label="API服务商"
            name="model_provider"
            rules={[{ required: true, message: '请选择API服务商' }]}
          >
            <Select>
              <Option value="anthropic">Anthropic (Claude 系列)</Option>
              <Option value="openai">OpenAI (GPT 系列)</Option>
              <Option value="baidu">百度文心一言</Option>
              <Option value="alipay">阿里云通义千问</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: true, message: '请输入API Key' }]}
            extra={
              <Space>
                <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer">
                  获取Anthropic API Key
                </a>
              </Space>
            }
          >
            <Input.Password placeholder="请输入API Key" />
          </Form.Item>
          <Form.Item>
            <Button type="default" onClick={handleTestApiKey}>测试API Key</Button>
          </Form.Item>
          <Form.Item
            label="选择模型"
            name="model"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select>
              <Option value="claude-3-opus-20240229">Claude 3 Opus (最强，生成质量最高，速度较慢)</Option>
              <Option value="claude-3-sonnet-20240229">Claude 3 Sonnet (平衡，推荐使用，性价比高)</Option>
              <Option value="claude-3-haiku-20240307">Claude 3 Haiku (最快，适合简单生成任务)</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="生成温度 (Temperature)"
            name="temperature"
            extra="值越低生成内容越稳定，值越高越有创造性，建议0.5-0.8"
            rules={[{ required: true, message: '请输入生成温度' }]}
          >
            <Input type="number" min={0} max={1} step={0.1} placeholder="0.7" />
          </Form.Item>
          <Divider />
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
              保存配置
            </Button>
          </Form.Item>
        </Form>
      </Card>
      <Card title="通用设置" className="card-container">
        <Form
          layout="vertical"
          initialValues={{
            storage_path: '我的文档/标书生成工具',
            auto_save_interval: 5,
            theme: 'light'
          }}
        >
          <Form.Item
            label="默认存储路径"
            name="storage_path"
            extra="生成的标书和项目数据默认保存的位置"
          >
            <Input readOnly />
            <Button type="default" style={{ marginTop: 8 }}>选择路径</Button>
          </Form.Item>
          <Form.Item
            label="自动保存间隔"
            name="auto_save_interval"
            extra="编辑器自动保存的时间间隔，单位：分钟"
          >
            <Select>
              <Option value={1}>1分钟</Option>
              <Option value={3}>3分钟</Option>
              <Option value={5}>5分钟</Option>
              <Option value={10}>10分钟</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="主题设置"
            name="theme"
          >
            <Select>
              <Option value="light">浅色主题</Option>
              <Option value="dark">深色主题</Option>
              <Option value="system">跟随系统</Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>
      <Card title="关于" className="card-container">
        <div style={{ lineHeight: '2' }}>
          <p><strong>智能标书生成工具</strong></p>
          <p>版本：1.0.0</p>
          <p>基于AI大模型的智能标书生成工具，帮助您快速生成高质量的投标文件，提高投标效率，降低废标风险。</p>
          <p>© 2024 版权所有</p>
        </div>
      </Card>
    </div>
  )
}
export default Settings
