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

// ---- Admin API ----

export interface DashboardStats {
  total_patients: number;
  active_patients: number;
  total_doctors: number;
  total_departments: number;
  alerts_by_severity: Record<string, number>;
  glucose_control_rate: number;
  patient_registration_trend: Array<{ date: string; count: number }>;
}

export interface DepartmentItem {
  id: string;
  name: string;
  code: string;
  hospital_id: string | null;
  is_active: boolean;
  doctor_count: number;
  patient_count: number;
}

export interface DepartmentListResponse {
  items: DepartmentItem[];
  total: number;
}

export interface AdminDoctorItem {
  id: string;
  user_id: string;
  department_id: string;
  department_name: string;
  department_code: string;
  title: string;
  license_number: string | null;
  is_department_head: boolean;
  is_active: boolean;
  patient_count: number;
  last_login_at: string | null;
}

export interface AdminDoctorListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AdminDoctorItem[];
}

export interface AdminPatientItem {
  id: string;
  gender: string;
  birth_year: number;
  diabetes_type: string;
  hba1c_target: number;
  latest_glucose: number | null;
  alert_count: number;
  glucose_control_status: string;
}

export interface AdminPatientListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AdminPatientItem[];
}

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  timestamp: string;
}

export interface AuditLogListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AuditLogItem[];
}

export interface AdminConfigParams {
  fpg_diagnostic_threshold: number;
  hba1c_diagnostic_threshold: number;
  hba1c_treatment_target: number;
  elderly_hba1c_target: number;
  egfr_metformin_contraindication: number;
  severe_hyperglycemia_threshold: number;
  hypoglycemia_threshold: number;
}

export interface AdminConfigResponse {
  params: AdminConfigParams;
  config_version: number;
  versions: Array<{ version: number; updated_at: string }>;
}

export interface UpdateConfigRequest {
  fpg_diagnostic_threshold?: number;
  hba1c_diagnostic_threshold?: number;
  hba1c_treatment_target?: number;
  elderly_hba1c_target?: number;
  egfr_metformin_contraindication?: number;
  severe_hyperglycemia_threshold?: number;
  hypoglycemia_threshold?: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get('/admin/dashboard');
  return data;
}

export async function getAdminDepartments(): Promise<DepartmentListResponse> {
  const { data } = await api.get('/admin/departments');
  return data;
}

export async function createAdminDepartment(body: {
  name: string;
  code: string;
  hospital_id?: string;
}) {
  const { data } = await api.post('/admin/departments', body);
  return data;
}

export async function updateAdminDepartment(id: string, body: {
  name?: string;
  code?: string;
  is_active?: boolean;
}) {
  const { data } = await api.put(`/admin/departments/${id}`, body);
  return data;
}

export async function deleteAdminDepartment(id: string) {
  const { data } = await api.delete(`/admin/departments/${id}`);
  return data;
}

export async function getAdminDoctors(params?: {
  page?: number;
  page_size?: number;
  department_id?: string;
}): Promise<AdminDoctorListResponse> {
  const { data } = await api.get('/admin/doctors', { params });
  return data;
}

export async function assignDoctorDepartment(doctorId: string, departmentId: string) {
  const { data } = await api.post(`/admin/doctors/${doctorId}/assign-department`, {
    department_id: departmentId,
  });
  return data;
}

export async function toggleDoctorActive(doctorId: string) {
  const { data } = await api.put(`/admin/doctors/${doctorId}/toggle-active`);
  return data;
}

export async function getAdminPatients(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  department_id?: string;
  risk_level?: string;
  glucose_control?: string;
}): Promise<AdminPatientListResponse> {
  const { data } = await api.get('/admin/patients', { params });
  return data;
}

export async function getAuditLogs(params?: {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  resource_type?: string;
}): Promise<AuditLogListResponse> {
  const { data } = await api.get('/admin/audit-logs', { params });
  return data;
}

export async function getAdminConfig(): Promise<AdminConfigResponse> {
  const { data } = await api.get('/admin/config');
  return data;
}

export async function updateAdminConfig(body: UpdateConfigRequest) {
  const { data } = await api.post('/admin/config', body);
  return data;
}

export async function resetAdminConfig() {
  const { data } = await api.post('/admin/config/reset');
  return data;
}
