import { useState, useMemo } from 'react';
import {
  Typography,
  Steps,
  Form,
  Select,
  Input,
  InputNumber,
  Radio,
  Button,
  Card,
  Result,
  Spin,
  Divider,
  Descriptions,
  message,
} from 'antd';
import { FormOutlined, CheckCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import type { QuestionItem, AnswerItem } from '../../lib/api';
import { getQuestionnaire, submitAnswers } from '../../lib/api';
import { mockQuestionnaire, mockSubmitAnswers } from '../../lib/mock';

const { Title, Text } = Typography;
const { Step } = Steps;
const { TextArea } = Input;

type StepKey = 'questionnaire' | 'confirm' | 'result';

const STEP_ITEMS = [
  { key: 'questionnaire' as StepKey, title: '填写问卷', icon: <FormOutlined /> },
  { key: 'confirm' as StepKey, title: '确认提交', icon: <CheckCircleOutlined /> },
  { key: 'result' as StepKey, title: 'AI 总结', icon: <FileTextOutlined /> },
];

// Default patient_data to use as mock input
const DEFAULT_PATIENT_DATA = {
  chief_complaint: '常规复诊',
  diabetes_type: '2型糖尿病',
  treatment_stage: '常规复诊',
  last_visit_findings: '',
  hba1c: 7.2,
};

function isQuestionVisible(question: QuestionItem, answers: Record<string, string>): boolean {
  if (!question.depends_on) return true;
  const dep = question.depends_on;
  const parentAnswer = answers[dep.question_id];
  if (!parentAnswer) return false;
  if (dep.matches_any) {
    return dep.matches_any.includes(parentAnswer);
  }
  return true;
}

function buildAnswerList(answers: Record<string, string>): AnswerItem[] {
  return Object.entries(answers)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([question_id, answer_value]) => ({ question_id, answer_value }));
}

function getAnswerLabel(question: QuestionItem, value: string): string {
  if (question.answer_type === 'boolean') {
    return value === 'true' || value === '是' ? '是' : '否';
  }
  return value;
}

export default function PreConsultation() {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [doctorSummary, setDoctorSummary] = useState('');
  const [summaryData, setSummaryData] = useState<Record<string, string> | null>(null);
  const [questionnaireFetched, setQuestionnaireFetched] = useState(false);

  const [form] = Form.useForm();

  // Fetch questionnaire on first load
  const fetchQuestionnaire = async () => {
    setLoading(true);
    try {
      const data = await getQuestionnaire(DEFAULT_PATIENT_DATA);
      if (data && data.questions && data.questions.length > 0) {
        setQuestions(data.questions);
      }
    } catch {
      // Fallback to mock
      const mock = mockQuestionnaire(DEFAULT_PATIENT_DATA);
      setQuestions(mock.questions);
    }
    setQuestionnaireFetched(true);
    setLoading(false);
  };

  // Visible questions considering conditional logic
  const visibleQuestions = useMemo(() => {
    return questions.filter((q) => isQuestionVisible(q, answers));
  }, [questions, answers]);

  // On step change: if entering questionnaire step and not yet loaded, fetch
  const handleStepChange = (step: number) => {
    if (step === 0 && !questionnaireFetched) {
      fetchQuestionnaire();
    }
    if (step === 1) {
      // Collect answers from form before confirming
      const formValues = form.getFieldsValue();
      const merged: Record<string, string> = { ...answers };
      Object.entries(formValues).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          merged[key] = String(value);
        }
      });
      setAnswers(merged);
    }
    setCurrentStep(step);
  };

  const handleConfirmSubmit = async () => {
    const answerList = buildAnswerList(answers);
    setLoading(true);
    try {
      const data = await submitAnswers(answerList, DEFAULT_PATIENT_DATA);
      setDoctorSummary(data.doctor_summary);
      setSummaryData(data.summary as unknown as Record<string, string>);
    } catch {
      const mock = mockSubmitAnswers(answerList, DEFAULT_PATIENT_DATA);
      setDoctorSummary(mock.doctor_summary);
      setSummaryData(mock.summary as unknown as Record<string, string>);
    }
    setLoading(false);
    setCurrentStep(2);
  };

  const handleRestart = () => {
    setAnswers({});
    setDoctorSummary('');
    setSummaryData(null);
    form.resetFields();
    setQuestionnaireFetched(false);
    setQuestions([]);
    setCurrentStep(0);
  };

  // ── Step 0: Questionnaire ──
  const renderQuestionnaire = () => {
    if (loading && questions.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" tip="正在生成个性化问卷..." />
        </div>
      );
    }

    if (!questionnaireFetched && questions.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Button type="primary" size="large" onClick={fetchQuestionnaire} loading={loading}>
            开始填写问卷
          </Button>
        </div>
      );
    }

    return (
      <Form form={form} layout="vertical" initialValues={answers} style={{ maxWidth: 600, margin: '0 auto' }}>
        {visibleQuestions.map((q) => (
          <Form.Item
            key={q.question_id}
            name={q.question_id}
            label={
              <span>
                {q.question_text}
                {q.required && <span style={{ color: '#ff4d4f', marginLeft: 4 }}>*</span>}
              </span>
            }
            rules={q.required ? [{ required: true, message: '请回答此问题' }] : []}
          >
            {renderQuestionInput(q)}
          </Form.Item>
        ))}

        <Form.Item style={{ textAlign: 'center', marginTop: 24 }}>
          <Button
            type="primary"
            size="large"
            onClick={() => {
              form
                .validateFields()
                .then((values) => {
                  const merged: Record<string, string> = { ...answers };
                  Object.entries(values).forEach(([key, value]) => {
                    if (value !== undefined && value !== null) {
                      merged[key] = String(value);
                    }
                  });
                  setAnswers(merged);
                  setCurrentStep(1);
                })
                .catch(() => {
                  message.warning('请完成所有必答题后再继续');
                });
            }}
          >
            下一步：确认答案
          </Button>
        </Form.Item>
      </Form>
    );
  };

  const renderQuestionInput = (q: QuestionItem) => {
    switch (q.answer_type) {
      case 'select':
        return (
          <Select placeholder="请选择">
            {(q.options || []).map((opt) => (
              <Select.Option key={opt} value={opt}>
                {opt}
              </Select.Option>
            ))}
          </Select>
        );
      case 'boolean':
        return (
          <Radio.Group>
            <Radio value="true">是</Radio>
            <Radio value="false">否</Radio>
          </Radio.Group>
        );
      case 'number':
        return <InputNumber style={{ width: '100%' }} placeholder="请输入数值" />;
      case 'text':
      default:
        return <TextArea rows={3} placeholder="请输入" />;
    }
  };

  // ── Step 1: Confirm ──
  const renderConfirm = () => {
    const answeredQuestions = visibleQuestions.filter((q) => answers[q.question_id]);
    return (
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <Card title="请确认以下信息无误" style={{ marginBottom: 24 }}>
          {answeredQuestions.map((q) => (
            <Descriptions key={q.question_id} column={1} size="small" bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label={q.question_text}>
                {getAnswerLabel(q, answers[q.question_id])}
              </Descriptions.Item>
            </Descriptions>
          ))}
          {answeredQuestions.length === 0 && <Text type="secondary">未填写任何问题</Text>}
        </Card>

        <div style={{ textAlign: 'center', display: 'flex', gap: 16, justifyContent: 'center' }}>
          <Button size="large" onClick={() => setCurrentStep(0)}>
            返回修改
          </Button>
          <Button type="primary" size="large" onClick={handleConfirmSubmit} loading={loading}>
            确认并生成AI总结
          </Button>
        </div>
      </div>
    );
  };

  // ── Step 2: Result ──
  const renderResult = () => {
    if (loading) {
      return (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" tip="AI正在分析您的问卷..." />
        </div>
      );
    }

    return (
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <Result
          status="success"
          title="问卷已提交"
          subTitle="您的问卷已生成结构化摘要，可在医生端查看"
        />

        {doctorSummary && (
          <Card title="AI 生成的就诊摘要" style={{ marginBottom: 16 }}>
            <Text>{doctorSummary}</Text>
          </Card>
        )}

        {summaryData && (
          <Card title="结构化摘要详情" style={{ marginBottom: 24 }}>
            {summaryData.chief_complaint && (
              <>
                <Text strong>主诉：</Text>
                <Text>{summaryData.chief_complaint}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.present_illness && (
              <>
                <Text strong>现病史：</Text>
                <Text>{summaryData.present_illness}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.past_history && (
              <>
                <Text strong>既往史：</Text>
                <Text>{summaryData.past_history}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.family_history && (
              <>
                <Text strong>家族史：</Text>
                <Text>{summaryData.family_history}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.social_history && (
              <>
                <Text strong>生活方式：</Text>
                <Text>{summaryData.social_history}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.medication_review && (
              <>
                <Text strong>用药回顾：</Text>
                <Text>{summaryData.medication_review}</Text>
                <Divider style={{ margin: '8px 0' }} />
              </>
            )}
            {summaryData.review_of_systems && (
              <>
                <Text strong>系统回顾：</Text>
                <Text>{summaryData.review_of_systems}</Text>
              </>
            )}
          </Card>
        )}

        <div style={{ textAlign: 'center' }}>
          <Button type="primary" size="large" onClick={handleRestart}>
            开始新的问卷
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>就诊前问卷</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
        请在就诊前完成以下问卷，帮助医生快速了解您的情况
      </Text>

      <Steps current={currentStep} style={{ marginBottom: 32 }}>
        {STEP_ITEMS.map((item) => (
          <Step key={item.key} title={item.title} icon={item.icon} />
        ))}
      </Steps>

      {currentStep === 0 && renderQuestionnaire()}
      {currentStep === 1 && renderConfirm()}
      {currentStep === 2 && renderResult()}
    </div>
  );
}
