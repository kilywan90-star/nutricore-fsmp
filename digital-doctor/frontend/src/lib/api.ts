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
