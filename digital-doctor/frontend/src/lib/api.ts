import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

export interface RiskAssessmentInput {
  age: number;
  bmi: number;
  waist_circumference: number;
  family_history: boolean;
  physical_activity: 'high' | 'moderate' | 'low';
  fasting_glucose: number;
  has_hypertension: boolean;
}

export interface RiskAssessmentResult {
  risk_level: string;
  score: number;
  max_score: number;
  factor_scores: Record<string, number>;
  recommendations: string[];
}

export async function assessRisk(input: RiskAssessmentInput): Promise<RiskAssessmentResult> {
  const { data } = await api.post('/patient/risk-assessment', input);
  return data;
}

export async function interpretReport(reportType: string, results: Record<string, number>) {
  const { data } = await api.post('/patient/report-interpret', { report_type: reportType, results });
  return data;
}

export async function getGlucoseStats(values: number[]) {
  const { data } = await api.post('/patient/glucose-stats', values);
  return data;
}

export async function chatWithCoach(input: {
  message: string;
  recent_fpg?: number[];
  recent_ppg?: number[];
  hba1c?: number;
  medications?: string[];
}) {
  const { data } = await api.post('/patient/health-coach', input);
  return data;
}

export async function getPatients(page = 1, search = '') {
  const { data } = await api.get('/doctor/patients', { params: { page, search } });
  return data;
}

export async function getPatientDetail(id: string) {
  const { data } = await api.get(`/doctor/patients/${id}`);
  return data;
}

export async function getPatientAlerts(id: string) {
  const { data } = await api.get(`/doctor/patients/${id}/alerts`);
  return data;
}
