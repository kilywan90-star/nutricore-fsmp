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

// ── Grassroots API ─────────────────────────────────────────────────

export interface ScreeningInput {
  name: string;
  village: string;
  age: number;
  gender: string;
  waist_circumference: number;
  fasting_glucose: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  family_history?: boolean;
  hospital_id?: string;
}

export interface ScreeningResult {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  risk_level: string;
  risk_score: number;
  max_score: number;
  factor_scores: Record<string, number>;
  referral_needed: boolean;
  recommendation: string;
}

export interface GrassrootsPatientItem {
  id: string;
  name: string;
  age: number;
  gender: string;
  village: string;
  diabetes_type: string | null;
  latest_fpg: number | null;
  risk_status: string | null;
  last_follow_up: string | null;
}

export interface FollowUpInput {
  glucose_value?: number;
  medication_adherent?: boolean;
  new_symptoms?: string;
  referral_needed?: boolean;
  referral_reason?: string;
  notes?: string;
  next_follow_up?: string;
}

export interface FollowUpResult {
  id: string;
  patient_id: string;
  glucose_value: number | null;
  medication_adherent: boolean | null;
  new_symptoms: string | null;
  referral_needed: boolean;
  followed_up_at: string;
  next_follow_up: string | null;
}

export interface GrassrootsDashboardData {
  total_managed: number;
  high_risk_count: number;
  overdue_follow_ups: number;
  pending_referrals: number;
  screenings_this_month: number;
  today_screenings: number;
}

export interface SyncResult {
  status: string;
  synced: number;
  failed: number;
  errors: Array<{ id: string; action: string; error: string }>;
}

export interface SyncStatus {
  pending_count: number;
  failed_count: number;
  last_sync_time: string | null;
  recent_errors: Array<{ id: string; action: string; error: string }>;
}

export async function submitScreening(input: ScreeningInput): Promise<ScreeningResult> {
  const { data } = await api.post('/grassroots/screening', input);
  return data;
}

export async function getGrassrootsPatients(params?: {
  village?: string;
  risk_filter?: string;
  page?: number;
  page_size?: number;
}): Promise<GrassrootsPatientItem[]> {
  const { data } = await api.get('/grassroots/patients', { params });
  return data;
}

export async function recordFollowUp(
  patientId: string,
  input: FollowUpInput,
): Promise<FollowUpResult> {
  const { data } = await api.post(`/grassroots/patients/${patientId}/follow-up`, input);
  return data;
}

export async function getGrassrootsDashboard(
  hospitalId?: string,
): Promise<GrassrootsDashboardData> {
  const { data } = await api.get('/grassroots/dashboard', { params: { hospital_id: hospitalId } });
  return data;
}

export async function syncGrassrootsData(): Promise<SyncResult> {
  const { data } = await api.post('/grassroots/sync');
  return data;
}

export async function getSyncStatus(): Promise<SyncStatus> {
  const { data } = await api.get('/grassroots/sync/status');
  return data;
}

// ── Medical Record API ────────────────────────────────────────────────

export interface RecordListItem {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface RecordListResponse {
  patient_id: string;
  total: number;
  items: RecordListItem[];
}

export interface RecordVersion {
  version: number;
  content: Record<string, string>;
  markdown: string;
  edited_by: string;
  edited_at: string;
}

export interface MedicalRecordDetail {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  content: Record<string, string>;
  markdown: string;
  status: string;
  version: number;
  versions: RecordVersion[];
  created_at: string;
  updated_at: string;
}

export async function generateRecord(patientId: string, encounterData: Record<string, unknown>): Promise<MedicalRecordDetail> {
  const { data } = await api.post(`/doctor/patients/${patientId}/records/generate`, { encounter_data: encounterData });
  return data;
}

export async function generateDischargeRecord(patientId: string, admissionData: Record<string, unknown>): Promise<MedicalRecordDetail> {
  const { data } = await api.post(`/doctor/patients/${patientId}/records/generate-discharge`, { admission_data: admissionData });
  return data;
}

export async function listRecords(patientId: string, recordType?: string): Promise<RecordListResponse> {
  const { data } = await api.get(`/doctor/patients/${patientId}/records`, { params: { record_type: recordType } });
  return data;
}

export async function getRecordDetail(recordId: string): Promise<MedicalRecordDetail> {
  const { data } = await api.get(`/doctor/records/${recordId}`);
  return data;
}

export async function editRecord(recordId: string, content: Record<string, string>, markdown?: string): Promise<MedicalRecordDetail> {
  const { data } = await api.put(`/doctor/records/${recordId}`, { content, markdown });
  return data;
}

export async function finalizeRecord(recordId: string): Promise<{ id: string; status: string; updated_at: string }> {
  const { data } = await api.post(`/doctor/records/${recordId}/finalize`);
  return data;
}
