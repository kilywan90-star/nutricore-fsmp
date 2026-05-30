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

// ── Critical Alert API ────────────────────────────────────────────────

export interface CriticalAlertItem {
  id: string;
  patient_id: string;
  alert_type: string;
  severity: string;
  title: string;
  detail: string;
  value: number;
  detected_at: string;
  doctor_user_id: string | null;
  status: string;
  status_history: Array<{ status: string; timestamp: string; user_id: string | null; notes: string }> | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  escalated_to: string | null;
  resolution: string | null;
  closed_at: string | null;
}

export interface CriticalAlertListResponse {
  total: number;
  page: number;
  page_size: number;
  items: CriticalAlertItem[];
}

export interface CriticalAlertStats {
  open_count: number;
  acknowledged_count: number;
  resolved_count: number;
  escalated_count: number;
  expired_count: number;
}

export async function triggerCriticalAlert(patientId: string, params?: {
  alert_type?: string;
  value?: number;
}): Promise<CriticalAlertItem> {
  const { data } = await api.post('/doctor/critical-alerts', {
    patient_id: patientId,
    alert_type: params?.alert_type || 'severe_hyperglycemia',
    value: params?.value || 18.0,
  });
  return data;
}

export async function listCriticalAlerts(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<CriticalAlertListResponse> {
  const { data } = await api.get('/doctor/critical-alerts', { params });
  return data;
}

export async function acknowledgeCriticalAlert(
  alertId: string,
  body: { resolution: string; notes?: string },
): Promise<CriticalAlertItem> {
  const { data } = await api.post(`/doctor/critical-alerts/${alertId}/acknowledge`, body);
  return data;
}

export async function nurseConfirmCriticalAlert(alertId: string): Promise<CriticalAlertItem> {
  const { data } = await api.post(`/doctor/critical-alerts/${alertId}/nurse-confirm`);
  return data;
}

export async function getCriticalAlertStats(): Promise<CriticalAlertStats> {
  const { data } = await api.get('/doctor/critical-alerts/stats');
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

// ── Pre-consultation API ────────────────────────────────────────────────

export interface QuestionItem {
  question_id: string;
  question_text: string;
  answer_type: 'text' | 'select' | 'number' | 'boolean';
  options: string[] | null;
  required: boolean;
  depends_on: { question_id: string; matches_any?: string[] } | null;
}

export interface QuestionnaireResponse {
  questions: QuestionItem[];
}

export interface PreConsultSummary {
  chief_complaint: string;
  present_illness: string;
  past_history: string;
  family_history: string;
  social_history: string;
  medication_review: string;
  review_of_systems: string;
}

export interface SubmitAnswersResponse {
  summary: PreConsultSummary;
  doctor_summary: string;
}

export interface AnswerItem {
  question_id: string;
  answer_value: string;
}

export async function getQuestionnaire(patientData: Record<string, unknown>): Promise<QuestionnaireResponse> {
  const { data } = await api.post('/patient/pre-consultation/questionnaire', { patient_data: patientData });
  return data;
}

export async function submitAnswers(
  answers: AnswerItem[],
  patientData: Record<string, unknown>,
): Promise<SubmitAnswersResponse> {
  const { data } = await api.post('/patient/pre-consultation/submit', {
    answers,
    patient_data: patientData,
  });
  return data;
}

export async function getDoctorPreConsultation(patientId: string) {
  const { data } = await api.get(`/doctor/patients/${patientId}/pre-consultation`);
  return data;
}

// ── Prescription Review API ────────────────────────────────────────────

export interface DrugInfo {
  generic_name: string;
  generic_name_en: string;
  drug_class: string;
  brand_names: string[];
  dosage_range: {
    starting: string;
    usual: string;
    max: string;
    frequency: string;
    timing: string;
  };
  renal_adjustment: Array<{ egfr_min: number; egfr_max: number | null; dose: string }>;
  hepatic_warning: string;
  common_side_effects: string[];
  contraindications: string[];
  pregnancy_category: string;
}

export interface MedicationInput {
  name: string;
  dose: string;
  frequency: string;
}

export interface PrescriptionReviewIssue {
  severity: 'minor' | 'moderate' | 'major' | 'contraindicated';
  category: 'guideline_concordance' | 'drug_interaction' | 'renal_dosing' | 'hepatic_dosing' | 'contraindication';
  description: string;
  recommendation: string;
  guideline_ref: string;
}

export interface PrescriptionReviewResult {
  overall_rating: 'safe' | 'caution' | 'unsafe';
  issues: PrescriptionReviewIssue[];
  summary: string;
  diagnosis: string;
  medication_count: number;
  issue_count: number;
}

export interface DrugInteractionResult {
  drug_a: string;
  drug_b: string;
  severity: string;
  mechanism: string;
  recommendation: string;
}

export async function reviewPrescription(input: {
  diagnosis: string;
  medications: MedicationInput[];
  patient_data: Record<string, unknown>;
  lab_results: Record<string, unknown>;
}): Promise<PrescriptionReviewResult> {
  const { data } = await api.post('/doctor/prescriptions/review', input);
  return data;
}

export async function searchDrugs(query: string): Promise<{ items: DrugInfo[] }> {
  const { data } = await api.get('/doctor/drugs', { params: { q: query } });
  return data;
}

export async function checkDrugInteractions(
  medications: Array<{ drug_name: string }>,
): Promise<{ medications: string[]; interactions: DrugInteractionResult[] }> {
  const { data } = await api.post('/doctor/drugs/check-interactions', { medications });
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

// ── Admin API ────────────────────────────────────────────────────────

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

// ── Signature API ─────────────────────────────────────────────────────────

export interface SignatureResponse {
  id: string;
  user_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  signature_data: Record<string, unknown>;
  content_hash: string;
  previous_signature_id: string | null;
  created_at: string;
}

export interface AuditTrailItem {
  id: string;
  user_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  signature_data: Record<string, unknown>;
  content_hash: string;
  previous_signature_id: string | null;
  created_at: string;
}

export interface AuditTrailResponse {
  resource_type: string;
  resource_id: string;
  signatures: AuditTrailItem[];
}

export interface ChainVerificationItemResponse {
  signature_id: string;
  user_id: string;
  action: string;
  timestamp: string;
  verified: boolean;
  content_hash: string;
}

export interface ChainVerificationResponse {
  valid: boolean;
  signatures: ChainVerificationItemResponse[];
  broken_links: string[];
}

export interface CreateSignatureRequest {
  resource_type: string;
  resource_id: string;
  action: string;
  content: Record<string, unknown>;
  confirmation_token?: string;
}

export async function createSignature(
  input: CreateSignatureRequest,
): Promise<SignatureResponse> {
  const { data } = await api.post('/signatures', input);
  return data;
}

export async function getAuditTrail(
  resourceType: string,
  resourceId: string,
): Promise<AuditTrailResponse> {
  const { data } = await api.get(`/signatures/${resourceType}/${resourceId}`);
  return data;
}

export async function verifySignatureChain(
  resourceType: string,
  resourceId: string,
): Promise<ChainVerificationResponse> {
  const { data } = await api.post(`/signatures/verify/${resourceType}/${resourceId}`);
  return data;
}
