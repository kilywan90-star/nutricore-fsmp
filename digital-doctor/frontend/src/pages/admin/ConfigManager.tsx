import { useEffect, useState } from 'react';
import {
  Card, Form, InputNumber, Button, Space, Typography, Divider, Spin, Empty, message, Table, Popconfirm,
} from 'antd';
import { SaveOutlined, UndoOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  getAdminConfig,
  updateAdminConfig,
  resetAdminConfig,
  type AdminConfigParams,
} from '../../lib/api';

const { Title, Text } = Typography;

interface ConfigField {
  key: keyof AdminConfigParams;
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  unit: string;
}

const CONFIG_FIELDS: ConfigField[] = [
  {
    key: 'fpg_diagnostic_threshold',
    label: '空腹血糖诊断阈值',
    description: 'FPG >= 此值且重复2次，符合糖尿病诊断标准',
    min: 3.0,
    max: 20.0,
    step: 0.1,
    unit: 'mmol/L',
  },
  {
    key: 'hba1c_diagnostic_threshold',
    label: 'HbA1c诊断阈值',
    description: 'HbA1c >= 此值，符合糖尿病诊断标准',
    min: 3.0,
    max: 15.0,
    step: 0.1,
    unit: '%',
  },
  {
    key: 'hba1c_treatment_target',
    label: 'HbA1c治疗目标',
    description: '一般成人血糖控制目标：HbA1c < 此值',
    min: 3.0,
    max: 15.0,
    step: 0.1,
    unit: '%',
  },
  {
    key: 'elderly_hba1c_target',
    label: '老年HbA1c目标',
    description: '65岁以上或合并并发症患者的宽松目标',
    min: 3.0,
    max: 15.0,
    step: 0.1,
    unit: '%',
  },
  {
    key: 'egfr_metformin_contraindication',
    label: 'eGFR二甲双胍禁忌阈值',
    description: 'eGFR < 此值时，二甲双胍需减量或禁用',
    min: 1.0,
    max: 120.0,
    step: 1.0,
    unit: 'mL/min/1.73m²',
  },
  {
    key: 'severe_hyperglycemia_threshold',
    label: '严重高血糖阈值',
    description: '血糖 >= 此值时触发危急预警',
    min: 5.0,
    max: 50.0,
    step: 0.1,
    unit: 'mmol/L',
  },
  {
    key: 'hypoglycemia_threshold',
    label: '低血糖阈值',
    description: '血糖 <= 此值时触发低血糖预警',
    min: 1.0,
    max: 10.0,
    step: 0.1,
    unit: 'mmol/L',
  },
];

interface VersionRecord {
  version: number;
  updated_at: string;
}

export default function ConfigManager() {
  const [config, setConfig] = useState<AdminConfigParams | null>(null);
  const [configVersion, setConfigVersion] = useState(0);
  const [versions, setVersions] = useState<VersionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    let cancelled = false;
    async function fetchConfig() {
      try {
        const data = await getAdminConfig();
        if (!cancelled) {
          setConfig(data.params);
          setConfigVersion(data.config_version);
          setVersions(data.versions);
          form.setFieldsValue(data.params);
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || '加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchConfig();
    return () => { cancelled = true; };
  }, [form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const result = await updateAdminConfig(values);
      setConfigVersion(result.config_version);
      setConfig({ ...values } as AdminConfigParams);
      message.success(`配置已保存 (版本 ${result.config_version})`);
      // Refresh to get updated version list
      const data = await getAdminConfig();
      setVersions(data.versions);
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      const result = await resetAdminConfig();
      setConfig(result.params);
      setConfigVersion(result.config_version);
      form.setFieldsValue(result.params);
      message.success('已重置为默认值');
      const data = await getAdminConfig();
      setVersions(data.versions);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '重置失败');
    } finally {
      setSaving(false);
    }
  };

  const versionColumns: ColumnsType<VersionRecord> = [
    { title: '版本号', dataIndex: 'version', key: 'version', width: 80 },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 200,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
  ];

  if (loading) {
    return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  }

  if (error && !config) {
    return <Empty description={error} />;
  }

  return (
    <div>
      <Title level={4}>参数配置</Title>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {/* Main Config Form */}
        <Card
          title="指南参数阈值"
          extra={
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={saving}
              >
                保存配置
              </Button>
              <Popconfirm
                title="确认重置？"
                description="所有参数将恢复为默认值"
                onConfirm={handleReset}
                okText="确认"
                cancelText="取消"
              >
                <Button icon={<UndoOutlined />} danger>
                  恢复默认
                </Button>
              </Popconfirm>
            </Space>
          }
          style={{ flex: 1, minWidth: 480 }}
        >
          <Form form={form} layout="vertical">
            {CONFIG_FIELDS.map((field) => (
              <Form.Item
                key={field.key}
                name={field.key}
                label={
                  <span>
                    {field.label}
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      ({field.unit})
                    </Text>
                  </span>
                }
                extra={<Text type="secondary" style={{ fontSize: 12 }}>{field.description}</Text>}
                rules={[
                  { required: true, message: `请输入${field.label}` },
                ]}
              >
                <InputNumber
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  style={{ width: 200 }}
                />
              </Form.Item>
            ))}
          </Form>
        </Card>

        {/* Version History */}
        <Card title="版本历史" style={{ width: 280 }}>
          {versions.length === 0 ? (
            <Empty description="暂无版本记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Table<VersionRecord>
              columns={versionColumns}
              dataSource={versions}
              rowKey="version"
              size="small"
              pagination={false}
            />
          )}
          <Divider />
          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">当前版本: v{configVersion}</Text>
          </div>
        </Card>
      </div>
    </div>
  );
}
