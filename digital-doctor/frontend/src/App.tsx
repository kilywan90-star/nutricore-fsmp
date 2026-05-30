import { Routes, Route, Navigate } from 'react-router-dom';
import PatientHome from './pages/patient/HomePage';
import RiskAssessment from './pages/patient/RiskAssessment';
import ReportView from './pages/patient/ReportView';
import MedicationPage from './pages/patient/MedicationPage';
import GlucoseLog from './pages/patient/GlucoseLog';
import HealthCoach from './pages/patient/HealthCoach';
import DoctorDashboard from './pages/doctor/Dashboard';
import PatientList from './pages/doctor/PatientList';
import PatientDetail from './pages/doctor/PatientDetail';
import AlertPanel from './pages/doctor/AlertPanel';
import AdminLayout from './pages/admin/AdminLayout';
import AdminDashboard from './pages/admin/Dashboard';
import DepartmentManager from './pages/admin/DepartmentManager';
import AdminDoctorManager from './pages/admin/DoctorManager';
import ConfigManager from './pages/admin/ConfigManager';
import AuditLogViewer from './pages/admin/AuditLogViewer';

export default function App() {
  return (
    <Routes>
      <Route path="/patient" element={<PatientHome />} />
      <Route path="/patient/risk" element={<RiskAssessment />} />
      <Route path="/patient/report" element={<ReportView />} />
      <Route path="/patient/medication" element={<MedicationPage />} />
      <Route path="/patient/glucose" element={<GlucoseLog />} />
      <Route path="/patient/coach" element={<HealthCoach />} />
      <Route path="/doctor" element={<DoctorDashboard />} />
      <Route path="/doctor/patients" element={<PatientList />} />
      <Route path="/doctor/patients/:id" element={<PatientDetail />} />
      <Route path="/doctor/alerts" element={<AlertPanel />} />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="departments" element={<DepartmentManager />} />
        <Route path="doctors" element={<AdminDoctorManager />} />
        <Route path="config" element={<ConfigManager />} />
        <Route path="audit" element={<AuditLogViewer />} />
      </Route>
      <Route path="*" element={<Navigate to="/patient" replace />} />
    </Routes>
  );
}
