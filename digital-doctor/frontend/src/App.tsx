import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';

// ── Lazy-loaded pages ──────────────────────────────────────────────────
// Patient pages (most frequently visited)
const PatientHome = lazy(() => import('./pages/patient/HomePage'));
const RiskAssessment = lazy(() => import('./pages/patient/RiskAssessment'));
const ReportView = lazy(() => import('./pages/patient/ReportView'));
const MedicationPage = lazy(() => import('./pages/patient/MedicationPage'));
const GlucoseLog = lazy(() => import('./pages/patient/GlucoseLog'));
const HealthCoach = lazy(() => import('./pages/patient/HealthCoach'));

// Doctor pages
const DoctorDashboard = lazy(() => import('./pages/doctor/Dashboard'));
const PatientList = lazy(() => import('./pages/doctor/PatientList'));
const PatientDetail = lazy(() => import('./pages/doctor/PatientDetail'));
const ReferralManager = lazy(() => import('./pages/doctor/ReferralManager'));
const ConsultationRoom = lazy(() => import('./pages/doctor/ConsultationRoom'));

// Admin pages (least visited — deepest split)
const AlertPanel = lazy(() => import('./pages/doctor/AlertPanel'));

// ── Fallback ───────────────────────────────────────────────────────────
const PageFallback = (
  <div style={{ padding: 48, textAlign: 'center' }}>
    <Spin size="large" tip="加载中..." />
  </div>
);

export default function App() {
  return (
    <Suspense fallback={PageFallback}>
      <Routes>
        {/* Patient routes */}
        <Route path="/patient" element={<PatientHome />} />
        <Route path="/patient/risk" element={<RiskAssessment />} />
        <Route path="/patient/report" element={<ReportView />} />
        <Route path="/patient/medication" element={<MedicationPage />} />
        <Route path="/patient/glucose" element={<GlucoseLog />} />
        <Route path="/patient/coach" element={<HealthCoach />} />

        {/* Doctor routes */}
        <Route path="/doctor" element={<DoctorDashboard />} />
        <Route path="/doctor/patients" element={<PatientList />} />
        <Route path="/doctor/patients/:id" element={<PatientDetail />} />

        {/* Alerts (admin/deep split) */}
        <Route path="/doctor/alerts" element={<AlertPanel />} />

        {/* Medical consortium — referrals & consultations */}
        <Route path="/doctor/referrals" element={<ReferralManager />} />
        <Route path="/doctor/consultations" element={<ConsultationRoom />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/patient" replace />} />
      </Routes>
    </Suspense>
  );
}
