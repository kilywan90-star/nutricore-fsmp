import type { RiskAssessmentResult } from './api';

/** Mock risk assessment result for demo mode */
export const mockRiskResult: RiskAssessmentResult = {
  risk_level: '中危',
  score: 12,
  max_score: 45,
  factor_scores: {
    age_score: 4,
    bmi_score: 3,
    waist_score: 0,
    family_score: 0,
    activity_score: 2,
    glucose_score: 3,
    hypertension_score: 0,
  },
  recommendations: [
    '建议3个月后复查空腹血糖，并行OGTT筛查',
    '建议每日主食控制在250-400g，减少含糖饮料摄入',
  ],
};

/** Mock glucose records for demo charts */
export const mockGlucoseRecords = [
  { date: '2026-05-24', fasting: 6.5, postPr: 9.2 },
  { date: '2026-05-25', fasting: 6.8, postPr: 8.8 },
  { date: '2026-05-26', fasting: 7.0, postPr: 10.1 },
  { date: '2026-05-27', fasting: 6.3, postPr: 9.5 },
  { date: '2026-05-28', fasting: 6.9, postPr: 8.2 },
  { date: '2026-05-29', fasting: 7.2, postPr: 9.8 },
  { date: '2026-05-30', fasting: 7.0, postPr: 10.3 },
];

/** Mock patient list for demo mode */
export const mockPatients = [
  {
    id: 'p-001',
    gender: 'M',
    birth_year: 1965,
    diabetes_type: 'type2',
    hba1c_target: 7.0,
    latest_glucose: 7.2,
    alert_count: 2,
  },
  {
    id: 'p-002',
    gender: 'F',
    birth_year: 1980,
    diabetes_type: 'type2',
    hba1c_target: 7.0,
    latest_glucose: 6.5,
    alert_count: 0,
  },
  {
    id: 'p-003',
    gender: 'M',
    birth_year: 1972,
    diabetes_type: 'type2',
    hba1c_target: 8.0,
    latest_glucose: 9.8,
    alert_count: 3,
  },
  {
    id: 'p-004',
    gender: 'F',
    birth_year: 1958,
    diabetes_type: 'type2',
    hba1c_target: 8.0,
    latest_glucose: 6.8,
    alert_count: 1,
  },
];

/** Mock patient detail for demo mode */
export const mockPatientDetail = {
  id: 'p-001',
  gender: 'M',
  birth_year: 1965,
  diabetes_type: 'type2',
  diagnosis_date: '2020-03-15',
  hba1c_target: 7.0,
  glucose_records: [
    { id: 'g-001', value_mmol_l: 6.5, measure_type: 'fasting', recorded_at: '2026-05-30T07:00:00', notes: '' },
    { id: 'g-002', value_mmol_l: 9.2, measure_type: 'post_prandial', recorded_at: '2026-05-30T12:30:00', notes: '' },
    { id: 'g-003', value_mmol_l: 7.0, measure_type: 'fasting', recorded_at: '2026-05-29T07:00:00', notes: '' },
    { id: 'g-004', value_mmol_l: 8.5, measure_type: 'post_prandial', recorded_at: '2026-05-29T12:30:00', notes: '午餐后散步15分钟' },
    { id: 'g-005', value_mmol_l: 6.8, measure_type: 'fasting', recorded_at: '2026-05-28T07:00:00', notes: '' },
  ],
  lab_reports: [
    {
      id: 'lr-001',
      report_type: 'blood_glucose_panel',
      report_date: '2026-05-28',
      results: { fpg: 7.0, hba1c: 7.2, ppg_2h: 10.1 },
      ai_interpretation: '空腹血糖7.0mmol/L，已达糖尿病诊断标准；HbA1c 7.2%提示近3月血糖控制未达标。建议调整治疗方案。',
    },
  ],
  alerts: [
    {
      id: 'a-001',
      alert_type: 'consecutive_high_fpg',
      severity: 'warning',
      title: '空腹血糖持续偏高',
      detail: '连续3天空腹血糖≥7.0mmol/L',
      acknowledged: false,
      created_at: '2026-05-30T07:05:00',
    },
    {
      id: 'a-002',
      alert_type: 'missed_logging',
      severity: 'warning',
      title: '连续2天未记录血糖',
      detail: '上次记录时间：05月25日，请提醒患者恢复血糖监测',
      acknowledged: false,
      created_at: '2026-05-28T08:00:00',
    },
  ],
};
