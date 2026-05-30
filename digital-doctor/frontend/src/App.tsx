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

// Alert + record editor (deep split)
const AlertPanel = lazy(() => import('./pages/doctor/AlertPanel'));
const RecordEditor = lazy(() => import('./pages/doctor/RecordEditor'));

// Grassroots pages (community health worker)
const GrassrootsLayout = lazy(() => import('./pages/grassroots/GrassrootsLayout'));
const GrassrootsHome = lazy(() => import('./pages/grassroots/GrassrootsHome'));
const ScreeningForm = lazy(() => import('./pages/grassroots/ScreeningForm'));
const FollowUpList = lazy(() => import('./pages/grassroots/FollowUpList'));
const FollowUpForm = lazy(() => import('./pages/grassroots/FollowUpForm'));
const PatientCards = lazy(() => import('./pages/grassroots/PatientCards'));

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
        <Route path="/doctor/patients/:id/records" element={<RecordEditor />} />

        {/* Alerts (admin/deep split) */}
        <Route path="/doctor/alerts" element={<AlertPanel />} />

        {/* Grassroots routes — community health worker, no auth required */}
        <Route path="/grassroots" element={<GrassrootsLayout />}>
          <Route index element={<GrassrootsHome />} />
          <Route path="screening" element={<ScreeningForm />} />
          <Route path="follow-up" element={<FollowUpList />} />
          <Route path="follow-up/:id" element={<FollowUpForm />} />
          <Route path="patients" element={<PatientCards />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/patient" replace />} />
      </Routes>
    </Suspense>
  );
}
