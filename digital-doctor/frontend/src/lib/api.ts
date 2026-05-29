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

export interface ReportInterpretResult {
  status: string;
  status_label: string;
  items: Array<{ item: string; value: number; status: string }>;
  interpretation: string;
}

export interface GlucoseStats {
  count: number;
  avg: number | null;
  max: number | null;
  min: number | null;
  std: number | null;
  time_in_range?: {
    in_range_pct: number;
    above_range_pct: number;
    below_range_pct: number;
  } | null;
}

export interface CoachReply {
  reply: string;
  is_urgent: boolean;
}

export async function assessRisk(input: RiskAssessmentInput): Promise<RiskAssessmentResult> {
  const { data } = await api.post('/patient/risk-assessment', input);
  return data;
}

export async function interpretReport(reportType: string, results: Record<string, number>): Promise<ReportInterpretResult> {
  const { data } = await api.post('/patient/report-interpret', { report_type: reportType, results });
  return data;
}

export async function getGlucoseStats(values: number[]): Promise<GlucoseStats> {
  const { data } = await api.post('/patient/glucose-stats', values);
  return data;
}

export async function chatWithCoach(input: {
  message: string;
  recent_fpg?: number[];
  recent_ppg?: number[];
  hba1c?: number;
  medications?: string[];
}): Promise<CoachReply> {
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
