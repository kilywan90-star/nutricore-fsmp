import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Menu, Button, Space, message, Progress, Drawer, Tabs, Divider } from 'antd'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  MagicOutlined,
  ExportOutlined,
  SettingOutlined
} from '@ant-design/icons'
// 后续引入Tiptap编辑器
const { Sider, Content } = Layout
const { TabPane } = Tabs
const Editor: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateProgress, setGenerateProgress] = useState(0)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [activeTab, setActiveTab] = useState('requirements')
  const [content, setContent] = useState('')
  useEffect(() => {
    loadProjectData()
  }, [projectId])
  const loadProjectData = async () => {
    setLoading(true)
    try {
      // 后续对接API，加载项目数据和标书内容
      setContent('# 标书内容\n\n这是标书的正文部分，AI生成的内容会显示在这里，您也可以手动编辑。')
      message.success('项目数据加载成功')
    } catch (error) {
      message.error('加载项目数据失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }
  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateProgress(0)
    try {
      // 模拟生成进度
      const interval = setInterval(() => {
        setGenerateProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval)
            setGenerating(false)
            message.success('标书生成完成')
            return 100
          }
          return prev + 10
        })
      }, 500)
    } catch (error) {
      message.error('生成失败')
      setGenerating(false)
    }
  }
  const handleSave = async () => {
    try {
      // 后续对接保存API
      message.success('保存成功')
    } catch (error) {
      message.error('保存失败')
    }
  }
  const handleExport = (type: 'docx' | 'pdf') => {
    message.info(`导出为${type.toUpperCase()}功能开发中`)
  }
  const menuItems = [
    {
      key: '1',
      label: '商务标',
      icon: <FileTextOutlined />,
      children: [
        { key: '1-1', label: '封面' },
        { key: '1-2', label: '投标书' },
        { key: '1-3', label: '法定代表人身份证明' },
        { key: '1-4', label: '授权委托书' },
        { key: '1-5', label: '商务偏离表' },
        { key: '1-6', label: '资格证明文件' },
        { key: '1-7', label: '业绩证明材料' }
      ]
    },
    {
      key: '2',
      label: '技术标',
      icon: <FileTextOutlined />,
      children: [
        { key: '2-1', label: '技术方案' },
        { key: '2-2', label: '项目实施计划' },
        { key: '2-3', label: '人员配置' },
        { key: '2-4', label: '质量保证措施' },
        { key: '2-5', label: '服务承诺' },
        { key: '2-6', label: '技术偏离表' }
      ]
    },
    {
      key: '3',
      label: '价格标',
      icon: <FileTextOutlined />,
      children: [
        { key: '3-1', label: '开标一览表' },
        { key: '3-2', label: '分项报价表' },
        { key: '3-3', label: '报价说明' }
      ]
    }
  ]
  return (
    <Layout style={{ height: '100%', background: '#fff' }}>
      {/* 顶部工具栏 */}
      <div style={{
        height: 64,
        padding: '0 16px',
        borderBottom: '1px solid #e8e8e8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#fff'
      }}>
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/project')}
          >
            返回项目
          </Button>
          <span style={{ fontSize: 16, fontWeight: 500 }}>
            编辑标书 - 项目{projectId}
          </span>
        </Space>
        <Space>
          {generating && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12 }}>生成进度:</span>
              <Progress percent={generateProgress} size="small" style={{ width: 120 }} />
            </div>
          )}
          <Button
            type="primary"
            icon={<MagicOutlined />}
            onClick={handleGenerate}
            loading={generating}
            disabled={generating}
          >
            一键生成
          </Button>
          <Button
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={loading}
          >
            保存
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            onClick={() => message.info('校验功能开发中')}
          >
            智能校验
          </Button>
          <Button
            icon={<ExportOutlined />}
            onClick={() => handleExport('docx')}
          >
            导出Word
          </Button>
          <Button
            icon={<ExportOutlined />}
            onClick={() => handleExport('pdf')}
          >
            导出PDF
          </Button>
          <Button
            icon={<SettingOutlined />}
            onClick={() => setDrawerVisible(true)}
          />
        </Space>
      </div>
      <Layout>
        {/* 左侧目录 */}
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          width={240}
          style={{ background: '#fff', borderRight: '1px solid #e8e8e8' }}
        >
          <Menu
            mode="inline"
            defaultSelectedKeys={['1-1']}
            defaultOpenKeys={['1']}
            items={menuItems}
            style={{ height: '100%', border: 'none' }}
          />
        </Sider>
        {/* 中间编辑区 */}
        <Content style={{ padding: 24, overflow: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '100px 0' }}>
              加载中...
            </div>
          ) : (
            <div style={{
              maxWidth: 900,
              margin: '0 auto',
              minHeight: '100%',
              background: '#fff',
              padding: 40,
              boxShadow: '0 0 10px rgba(0,0,0,0.05)'
            }}>
              {/* 后续替换为Tiptap编辑器 */}
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                style={{
                  width: '100%',
                  minHeight: '800px',
                  padding: 16,
                  fontSize: 14,
                  lineHeight: 1.8,
                  border: '1px solid #e8e8e8',
                  borderRadius: 4,
                  fontFamily: 'inherit'
                }}
              />
            </div>
          )}
        </Content>
      </Layout>
      {/* 右侧设置抽屉 */}
      <Drawer
        title="标书设置"
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="招标要求" key="requirements">
            <div>
              <p><strong>项目名称:</strong> XX政府智慧园区建设项目投标</p>
              <p><strong>招标单位:</strong> XX市政府采购中心</p>
              <p><strong>投标截止日期:</strong> 2024-06-30</p>
              <Divider />
              <h4>核心要求:</h4>
              <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                <li>具备系统集成一级资质</li>
                <li>近3年有3个以上同类项目经验</li>
                <li>项目团队至少有5人具备PMP证书</li>
                <li>服务期要求3年免费维保</li>
              </ul>
            </div>
          </TabPane>
          <TabPane tab="生成设置" key="generate">
            <p>生成设置功能开发中...</p>
          </TabPane>
          <TabPane tab="模板选择" key="template">
            <p>模板选择功能开发中...</p>
          </TabPane>
        </Tabs>
      </Drawer>
    </Layout>
  )
}
export default Editor
