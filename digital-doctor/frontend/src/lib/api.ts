import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// ---- Types ----

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
  std?: number | null;
  time_in_range?: { in_range_pct: number; above_range_pct: number; below_range_pct: number } | null;
}

export interface CoachReply {
  reply: string;
  is_urgent: boolean;
}

export interface PatientListItem {
  id: string;
  gender: string;
  birth_year: number;
  diabetes_type: string;
  hba1c_target: number;
  latest_glucose: number | null;
  alert_count: number;
}

export interface PatientListResponse {
  total: number;
  page: number;
  page_size: number;
  items: PatientListItem[];
}

export interface GlucoseRecord {
  id: string;
  value_mmol_l: number;
  measure_type: string;
  recorded_at: string;
  notes: string | null;
}

export interface LabReportItem {
  id: string;
  report_type: string;
  report_date: string;
  results: Record<string, number>;
  ai_interpretation: string;
}

export interface AlertItem {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  detail: string;
  acknowledged: boolean;
  created_at: string;
}

export interface PatientDetailData {
  id: string;
  gender: string;
  birth_year: number;
  diabetes_type: string;
  diagnosis_date: string | null;
  hba1c_target: number;
  glucose_records: GlucoseRecord[];
  lab_reports: LabReportItem[];
  alerts: AlertItem[];
}

export interface DoctorAlertItem {
  id: string;
  patient_id: string;
  alert_type: string;
  severity: string;
  title: string;
  detail: string;
  acknowledged: boolean;
  created_at: string;
}

// ---- Patient API ----

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

// ---- Doctor API ----

export async function getPatients(page = 1, pageSize = 20, search = ''): Promise<PatientListResponse> {
  const { data } = await api.get('/doctor/patients', { params: { page, page_size: pageSize, search } });
  return data;
}

export async function getPatientDetail(id: string): Promise<PatientDetailData> {
  const { data } = await api.get(`/doctor/patients/${id}`);
  return data;
}

export async function getPatientAlerts(id: string) {
  const { data } = await api.get(`/doctor/patients/${id}/alerts`);
  return data;
}

export async function acknowledgeAlert(alertId: string) {
  const { data } = await api.post(`/doctor/alerts/${alertId}/acknowledge`);
  return data;
}

export async function getAllAlerts(params?: {
  severity?: string;
  page?: number;
  page_size?: number;
}) {
  const { data } = await api.get('/doctor/alerts', { params });
  return data;
}

// ── Hospital & Admin API ─────────────────────────────────────────────

export interface HospitalItem {
  id: string;
  name: string;
  code: string;
  address: string | null;
  level: string | null;
  is_active: boolean;
  department_count: number;
  doctor_count: number;
}

export interface HospitalListResponse {
  items: HospitalItem[];
  total: number;
}

export interface HospitalStats {
  hospital_id: string;
  hospital_name: string;
  hospital_code: string;
  level: string | null;
  doctor_count: number;
  department_count: number;
  patient_count: number;
  pending_transfer_count: number;
}

export interface TransferItem {
  id: string;
  patient_id: string;
  from_hospital_id: string;
  from_hospital_name: string;
  to_hospital_id: string;
  to_hospital_name: string;
  requested_by: string;
  approved_by: string | null;
  status: string;
  reason: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TransferListResponse {
  total: number;
  page: number;
  page_size: number;
  items: TransferItem[];
}

export async function getHospitals(): Promise<HospitalListResponse> {
  const { data } = await api.get('/admin/hospitals');
  return data;
}

export async function createHospital(input: {
  name: string;
  code: string;
  address?: string;
  level?: string;
}): Promise<HospitalItem> {
  const { data } = await api.post('/admin/hospitals', input);
  return data;
}

export async function updateHospital(
  id: string,
  input: { name?: string; address?: string; level?: string; is_active?: boolean },
): Promise<HospitalItem> {
  const { data } = await api.put(`/admin/hospitals/${id}`, input);
  return data;
}

export async function getHospitalStats(id: string): Promise<HospitalStats> {
  const { data } = await api.get(`/admin/hospitals/${id}/stats`);
  return data;
}

export async function createTransfer(input: {
  patient_id: string;
  from_hospital_id: string;
  to_hospital_id: string;
  reason?: string;
}): Promise<TransferItem> {
  const { data } = await api.post('/admin/transfers', input);
  return data;
}

export async function approveTransfer(transferId: string, approved: boolean = true) {
  const { data } = await api.post(`/admin/transfers/${transferId}/approve`, { approved });
  return data;
}

export async function listTransfers(params?: {
  hospital_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<TransferListResponse> {
  const { data } = await api.get('/admin/transfers', { params });
  return data;
}

// ── Consortium (Medical Alliance) API ─────────────────────────────────

export interface ReferralEvaluation {
  referral_needed: boolean;
  urgency: 'routine' | 'urgent' | 'emergency';
  target_department: string;
  target_level: 'county' | 'municipal' | 'provincial';
  reason: string;
  criteria_met: number;
}

export interface ReferralTarget {
  id: string;
  name: string;
  code: string;
  address: string | null;
  level: string | null;
  department_id: string;
  department_name: string;
  doctor_count: number;
}

export interface ReferralItem {
  id: string;
  patient_id: string;
  from_hospital_id: string;
  from_hospital_name: string;
  from_doctor_id: string;
  to_hospital_id: string | null;
  to_hospital_name: string | null;
  to_doctor_id: string | null;
  target_department: string;
  urgency: string;
  target_level: string;
  reason: string;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface ReferralListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ReferralItem[];
}

export interface ConsultationItem {
  id: string;
  patient_id: string;
  requesting_doctor_id: string;
  consulting_doctor_id: string | null;
  consulting_hospital_id: string | null;
  status: string;
  clinical_question: string;
  ai_prepared_summary: Record<string, unknown> | null;
  consultation_notes: string | null;
  outcome: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ConsultationListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ConsultationItem[];
}

export async function evaluateReferral(input: {
  hba1c?: number;
  medication_count?: number;
  egfr?: number;
  has_active_foot_ulcer?: boolean;
  recent_cvd_event?: boolean;
  severe_hypoglycemia_episodes?: number;
  is_pregnant?: boolean;
  diabetes_type?: string;
}): Promise<ReferralEvaluation> {
  const { data } = await api.post('/doctor/referrals/evaluate', input);
  return data;
}

export async function searchReferralTargets(input: {
  location?: string;
  department: string;
  level: string;
}): Promise<ReferralTarget[]> {
  const { data } = await api.post('/doctor/referrals/search-targets', input);
  return data;
}

export async function createReferral(input: {
  patient_id: string;
  from_hospital_id: string;
  to_hospital_id?: string;
  to_doctor_id?: string;
  urgency: string;
  target_department: string;
  target_level: string;
  reason: string;
}): Promise<ReferralItem> {
  const { data } = await api.post('/doctor/referrals/create', input);
  return data;
}

export async function listReferrals(params?: {
  hospital_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ReferralListResponse> {
  const { data } = await api.get('/doctor/referrals', { params });
  return data;
}

export async function acceptReferral(referralId: string): Promise<{ id: string; status: string }> {
  const { data } = await api.put(`/doctor/referrals/${referralId}/accept`, { accepted: true });
  return data;
}

export async function getReferralSummary(referralId: string): Promise<{
  referral_id: string;
  clinical_summary: Record<string, unknown>;
}> {
  const { data } = await api.get(`/doctor/referrals/${referralId}/summary`);
  return data;
}

export async function createConsultation(input: {
  patient_id: string;
  clinical_question: string;
  consulting_doctor_id?: string;
  consulting_hospital_id?: string;
}): Promise<ConsultationItem> {
  const { data } = await api.post('/doctor/consultations', input);
  return data;
}

export async function listConsultations(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<ConsultationListResponse> {
  const { data } = await api.get('/doctor/consultations', { params });
  return data;
}

export async function getConsultation(sessionId: string): Promise<ConsultationItem> {
  const { data } = await api.get(`/doctor/consultations/${sessionId}`);
  return data;
}

export async function completeConsultation(
  sessionId: string,
  input: { notes?: string; outcome?: string },
): Promise<ConsultationItem> {
  const { data } = await api.post(`/doctor/consultations/${sessionId}/complete`, input);
  return data;
}
