import { Navigate, Route, Routes } from 'react-router-dom';
import LoginPage from './pages/auth/LoginPage';
import MicrosoftCallbackPage from './pages/auth/MicrosoftCallbackPage';
import AuthErrorPage from './pages/auth/AuthErrorPage';
import PortalShell from './pages/portal/PortalShell';
import WelcomePage from './pages/portal/WelcomePage';
import AppFramePage from './pages/portal/AppFramePage';
import CompaniesAdminPage from './pages/admin/CompaniesAdminPage';
import UsersAdminPage from './pages/admin/UsersAdminPage';
import ApplicationsAdminPage from './pages/admin/ApplicationsAdminPage';
import InstancesAdminPage from './pages/admin/InstancesAdminPage';
import AuditLogPage from './pages/admin/AuditLogPage';
import RequireAuth from './components/RequireAuth';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<MicrosoftCallbackPage />} />
      <Route path="/auth/error" element={<AuthErrorPage />} />

      <Route element={<RequireAuth><PortalShell /></RequireAuth>}>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/apps/:slug" element={<AppFramePage />} />
        <Route path="/admin/empresas" element={<CompaniesAdminPage />} />
        <Route path="/admin/usuarios" element={<UsersAdminPage />} />
        <Route path="/admin/aplicaciones" element={<ApplicationsAdminPage />} />
        <Route path="/admin/instancias" element={<InstancesAdminPage />} />
        <Route path="/admin/audit" element={<AuditLogPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
