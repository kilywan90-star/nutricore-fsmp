import type { RiskAssessmentResult, ReportInterpretResult, GlucoseStats, CoachReply } from './api';

export function mockAssessRisk(): RiskAssessmentResult {
  return {
    risk_level: '中危',
    score: 12,
    max_score: 45,
    factor_scores: {
      age_score: 4,
      bmi_score: 3,
      waist_score: 3,
      family_score: 0,
      activity_score: 2,
      glucose_score: 0,
      hypertension_score: 0,
    },
    recommendations: [
      '建议3个月后复查空腹血糖，并行OGTT筛查',
      '建议每日主食控制在250-400g，减少含糖饮料摄入',
    ],
  };
}

export function mockInterpretReport(reportType: string, results: Record<string, number>): ReportInterpretResult {
  if (reportType === 'blood_glucose_panel') {
    return {
      status: 'impaired',
      status_label: '临界异常',
      items: [
        { item: 'fpg', value: results.fpg ?? 6.5, status: 'impaired' },
        { item: 'hba1c', value: results.hba1c ?? 7.2, status: 'abnormal' },
      ],
      interpretation: '空腹血糖6.5mmol/L，处于糖尿病前期范围(6.1-7.0) 糖化血红蛋白7.2%，提示近3月血糖控制未达标(目标<7.0%) 建议定期监测血糖，遵医嘱调整治疗方案。',
    };
  }
  if (reportType === 'lipid_panel') {
    return {
      status: 'normal',
      status_label: '正常',
      items: [
        { item: 'tc', value: results.tc ?? 5.0, status: 'normal' },
        { item: 'ldl', value: results.ldl ?? 3.0, status: 'normal' },
        { item: 'hdl', value: results.hdl ?? 1.2, status: 'normal' },
        { item: 'tg', value: results.tg ?? 1.5, status: 'normal' },
      ],
      interpretation: '血脂检查结果均在正常范围。继续维持当前生活方式和治疗方案。',
    };
  }
  return {
    status: 'normal',
    status_label: '正常',
    items: [{ item: 'hba1c', value: results.hba1c ?? 6.8, status: 'impaired' }],
    interpretation: '检查结果均在正常范围。继续维持当前生活方式和治疗方案。',
  };
}

export function mockGlucoseStats(): GlucoseStats {
  return {
    count: 14,
    avg: 7.2,
    max: 12.5,
    min: 4.8,
    std: 1.8,
    time_in_range: {
      in_range_pct: 64.3,
      above_range_pct: 28.6,
      below_range_pct: 7.1,
    },
  };
}

export function mockCoachReply(message: string): CoachReply {
  const urgentKeywords = ['心慌', '出冷汗', '头晕', '看不清', '昏迷', '晕倒', '测不出', '很高', '低血糖', '发抖'];
  const isUrgent = urgentKeywords.some(kw => message.includes(kw));

  if (isUrgent) {
    return {
      reply: '您的症状需要立即引起重视。请立即测量血糖，如血糖<3.9mmol/L请立即补充15g速效碳水（如半杯果汁/3块方糖）；如症状持续不缓解，请立即拨打120或前往急诊。',
      is_urgent: true,
    };
  }

  if (message.includes('血糖高') || message.includes('控制不好')) {
    return {
      reply: '理解您的担忧。近期空腹血糖平均7.2mmol/L（目标<7.0），建议：1) 减少晚餐主食量至平时2/3 2) 餐后散步20分钟 3) 避免含糖饮料和甜点。持续记录血糖，下周复诊时带上记录给医生看。',
      is_urgent: false,
    };
  }

  if (message.includes('吃什么') || message.includes('饮食')) {
    return {
      reply: '建议选择低GI食物：全麦面包、燕麦、荞麦面、杂豆饭作为主食；蔬菜每日500g以上；蛋白质优选鱼虾去皮禽肉；水果选苹果、柚子、草莓，每次不超过100g，两餐之间食用。每日主食总量控制在250-400g。',
      is_urgent: false,
    };
  }

  return {
    reply: '记录得很好！继续坚持规律的血糖监测、合理饮食和适度运动。如果有任何不适或疑问，随时告诉我。',
    is_urgent: false,
  };
}

export interface MedicationItem {
  id: string;
  drug_name: string;
  dosage: string;
  frequency: string;
  time_of_day: string[];
  is_active: boolean;
}

export function mockMedications(): MedicationItem[] {
  return [
    { id: '1', drug_name: '二甲双胍', dosage: '500mg', frequency: 'bid', time_of_day: ['08:00', '18:00'], is_active: true },
    { id: '2', drug_name: '阿卡波糖', dosage: '50mg', frequency: 'tid', time_of_day: ['08:00', '12:00', '18:00'], is_active: true },
    { id: '3', drug_name: '达格列净', dosage: '10mg', frequency: 'qd', time_of_day: ['08:00'], is_active: true },
  ];
}

export interface GlucoseRecord {
  id: string;
  value_mmol_l: number;
  measure_type: string;
  recorded_at: string;
  notes: string;
}

export function mockGlucoseRecords(): GlucoseRecord[] {
  const records: GlucoseRecord[] = [];
  const now = new Date();
  for (let i = 13; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // Fasting
    records.push({
      id: `f-${i}`,
      value_mmol_l: parseFloat((5.5 + Math.random() * 3.5).toFixed(1)),
      measure_type: 'fasting',
      recorded_at: new Date(date.setHours(7, 0, 0, 0)).toISOString(),
      notes: '',
    });

    // Post-prandial
    date.setHours(10, 0, 0, 0);
    records.push({
      id: `p-${i}`,
      value_mmol_l: parseFloat((7.0 + Math.random() * 5).toFixed(1)),
      measure_type: 'post_prandial',
      recorded_at: new Date(date.setHours(10, 0, 0, 0)).toISOString(),
      notes: '',
    });
  }
  return records;
}

// ── Pre-consultation mocks ───────────────────────────────────────────────

import type { QuestionItem, QuestionnaireResponse, SubmitAnswersResponse, AnswerItem } from './api';

export function mockQuestionnaire(_patientData: Record<string, unknown>): QuestionnaireResponse {
  const questions: QuestionItem[] = [
    {
      question_id: 'chief_complaint',
      question_text: '您最近有哪些不适症状？',
      answer_type: 'select',
      options: ['多尿、多饮、多食、体重下降', '疲乏无力', '视力模糊', '皮肤瘙痒或感染', '无明显症状（体检发现）'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'symptom_duration',
      question_text: '上述症状持续了多长时间？',
      answer_type: 'select',
      options: ['1周以内', '1-4周', '1-3个月', '3-6个月', '6个月以上'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'diet_habit',
      question_text: '您的饮食偏好如何？',
      answer_type: 'select',
      options: ['偏甜食/含糖饮料', '偏油腻/高脂', '饮食较清淡均衡', '不规律'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'exercise_frequency',
      question_text: '您平时运动频率如何？',
      answer_type: 'select',
      options: ['几乎不运动', '每周1-2次', '每周3-4次', '每周5次以上'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'family_diabetes',
      question_text: '直系亲属中是否有糖尿病患者？',
      answer_type: 'select',
      options: ['有', '没有', '不清楚'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'other_conditions',
      question_text: '您是否患有其他慢性疾病？',
      answer_type: 'select',
      options: ['高血压', '高血脂', '冠心病', '肾脏疾病', '无'],
      required: true,
      depends_on: null,
    },
    {
      question_id: 'current_medications',
      question_text: '目前是否在服用其他药物？',
      answer_type: 'text',
      options: null,
      required: false,
      depends_on: null,
    },
  ];
  return { questions };
}

export function mockSubmitAnswers(answers: AnswerItem[], _patientData: Record<string, unknown>): SubmitAnswersResponse {
  const answerMap: Record<string, string> = {};
  answers.forEach((a) => {
    answerMap[a.question_id] = a.answer_value;
  });

  const chief = answerMap['chief_complaint'] || '常规复诊';
  const diet = answerMap['diet_habit'] || '未提供';
  const exercise = answerMap['exercise_frequency'] || '未提供';
  const family = answerMap['family_diabetes'] || '未提供';
  const duration = answerMap['symptom_duration'] || '未提供';

  return {
    summary: {
      chief_complaint: chief,
      present_illness: `症状持续时间：${duration}；发现方式：日常体检。`,
      past_history: `合并疾病：${answerMap['other_conditions'] || '无'}；其他用药：${answerMap['current_medications'] || '无'}。`,
      family_history: `糖尿病家族史：${family}。`,
      social_history: `饮食偏好：${diet}；运动：${exercise}。`,
      medication_review: '无特殊用药问题',
      review_of_systems: '无特殊系统回顾异常',
    },
    doctor_summary: `患者主诉：${chief}。现病史：症状持续时间${duration}，饮食偏好${diet}，运动频率${exercise}。既往史：合并${answerMap['other_conditions'] || '无其他慢性病'}。家族史：糖尿病家族史${family}。生活情况：饮食${diet}，运动${exercise}。`,
  };
}
