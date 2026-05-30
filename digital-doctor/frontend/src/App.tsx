import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';

// ── Patient pages ──
const PatientHome = lazy(() => import('./pages/patient/HomePage'));
const RiskAssessment = lazy(() => import('./pages/patient/RiskAssessment'));
const ReportView = lazy(() => import('./pages/patient/ReportView'));
const MedicationPage = lazy(() => import('./pages/patient/MedicationPage'));
const GlucoseLog = lazy(() => import('./pages/patient/GlucoseLog'));
const HealthCoach = lazy(() => import('./pages/patient/HealthCoach'));
const PreConsultation = lazy(() => import('./pages/patient/PreConsultation'));

// ── Doctor pages ──
const DoctorDashboard = lazy(() => import('./pages/doctor/Dashboard'));
const PatientList = lazy(() => import('./pages/doctor/PatientList'));
const PatientDetail = lazy(() => import('./pages/doctor/PatientDetail'));
const AlertPanel = lazy(() => import('./pages/doctor/AlertPanel'));
const DiagnosisPanel = lazy(() => import('./pages/doctor/DiagnosisPanel'));
const PrescriptionReview = lazy(() => import('./pages/doctor/PrescriptionReview'));
const RecordEditor = lazy(() => import('./pages/doctor/RecordEditor'));
const ReferralManager = lazy(() => import('./pages/doctor/ReferralManager'));
const ConsultationRoom = lazy(() => import('./pages/doctor/ConsultationRoom'));

// ── Admin pages ──
const AdminDashboard = lazy(() => import('./pages/admin/Dashboard'));
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'));
const DepartmentManager = lazy(() => import('./pages/admin/DepartmentManager'));
const DoctorManager = lazy(() => import('./pages/admin/DoctorManager'));
const ConfigManager = lazy(() => import('./pages/admin/ConfigManager'));
const AuditLogViewer = lazy(() => import('./pages/admin/AuditLogViewer'));

// ── Grassroots pages ──
const GrassrootsLayout = lazy(() => import('./pages/grassroots/GrassrootsLayout'));
const GrassrootsHome = lazy(() => import('./pages/grassroots/GrassrootsHome'));
const ScreeningForm = lazy(() => import('./pages/grassroots/ScreeningForm'));
const FollowUpList = lazy(() => import('./pages/grassroots/FollowUpList'));
const FollowUpForm = lazy(() => import('./pages/grassroots/FollowUpForm'));
const PatientCards = lazy(() => import('./pages/grassroots/PatientCards'));

const PageFallback = (
  <div style={{ padding: 48, textAlign: 'center' }}>
    <Spin size="large" tip="加载中..." />
  </div>
);

export default function App() {
  return (
    <Suspense fallback={PageFallback}>
      <Routes>
        {/* ── Patient (患者端) ── */}
        <Route path="/patient" element={<PatientHome />} />
        <Route path="/patient/risk" element={<RiskAssessment />} />
        <Route path="/patient/report" element={<ReportView />} />
        <Route path="/patient/medication" element={<MedicationPage />} />
        <Route path="/patient/glucose" element={<GlucoseLog />} />
        <Route path="/patient/coach" element={<HealthCoach />} />
        <Route path="/patient/pre-consultation" element={<PreConsultation />} />

        {/* ── Doctor (医生端) ── */}
        <Route path="/doctor" element={<DoctorDashboard />} />
        <Route path="/doctor/patients" element={<PatientList />} />
        <Route path="/doctor/patients/:id" element={<PatientDetail />} />
        <Route path="/doctor/patients/:id/records" element={<RecordEditor />} />
        <Route path="/doctor/patients/:id/diagnosis" element={<DiagnosisPanel />} />
        <Route path="/doctor/alerts" element={<AlertPanel />} />
        <Route path="/doctor/prescriptions/review" element={<PrescriptionReview />} />
        <Route path="/doctor/referrals" element={<ReferralManager />} />
        <Route path="/doctor/consultations" element={<ConsultationRoom />} />

        {/* ── Admin (管理后台) ── */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="departments" element={<DepartmentManager />} />
          <Route path="doctors" element={<DoctorManager />} />
          <Route path="config" element={<ConfigManager />} />
          <Route path="audit-logs" element={<AuditLogViewer />} />
        </Route>

        {/* ── Grassroots (基层版) ── */}
        <Route path="/grassroots" element={<GrassrootsLayout />}>
          <Route index element={<GrassrootsHome />} />
          <Route path="screening" element={<ScreeningForm />} />
          <Route path="follow-up" element={<FollowUpList />} />
          <Route path="follow-up/:id" element={<FollowUpForm />} />
          <Route path="patients" element={<PatientCards />} />
        </Route>

        {/* Catch-all → 患者首页 */}
        <Route path="*" element={<Navigate to="/patient" replace />} />
      </Routes>
    </Suspense>
  );
}
