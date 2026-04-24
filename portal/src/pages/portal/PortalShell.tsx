import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { api } from '../../lib/api';

export default function PortalShell() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  if (!user) return null;

  async function handleLogout() {
    try { await api.post('/auth/logout'); } catch { /* ignore */ }
    logout();
    navigate('/login', { replace: true });
  }

  async function handleSwitchCompany(companyId: string) {
    const r = await api.post<{ data: { access_token: string } }>('/auth/switch-company', { company_id: companyId });
    localStorage.setItem('maestro.access_token', r.data.data.access_token);
    window.location.reload();
  }

  return (
    <div className="min-h-screen grid grid-cols-[260px_1fr]">
      <aside className="bg-gray-900 text-white p-4 flex flex-col">
        <div className="text-lg font-bold mb-6">Maestro</div>
        <div className="mb-6">
          <div className="text-xs uppercase text-gray-400 mb-1">Usuario</div>
          <div className="font-medium">{user.display_name}</div>
          <div className="text-xs text-gray-400 truncate">{user.email}</div>
        </div>
        {user.companies.length > 1 && (
          <div className="mb-6">
            <label htmlFor="company" className="text-xs uppercase text-gray-400 mb-1 block">Empresa activa</label>
            <select id="company"
              value={user.active_company?.id ?? ''}
              onChange={(e) => handleSwitchCompany(e.target.value)}
              className="bg-gray-800 text-white w-full rounded px-2 py-1">
              {user.companies.filter(c => c.is_active).map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}
        <nav className="space-y-1 flex-1">
          <NavLink to="/" end
            className={({ isActive }) => `block px-3 py-2 rounded ${isActive ? 'bg-indigo-700' : 'hover:bg-gray-800'}`}>
            Inicio
          </NavLink>
          {/* Apps licenciadas se listarán aquí en próxima iteración vía GET /portal/my-apps */}
          {user.is_platform_admin && (
            <>
              <div className="mt-4 text-xs uppercase text-gray-400 px-3">Administración</div>
              <NavLink to="/admin/empresas" className="block px-3 py-2 rounded hover:bg-gray-800">Empresas</NavLink>
              <NavLink to="/admin/usuarios" className="block px-3 py-2 rounded hover:bg-gray-800">Usuarios</NavLink>
              <NavLink to="/admin/aplicaciones" className="block px-3 py-2 rounded hover:bg-gray-800">Aplicaciones</NavLink>
              <NavLink to="/admin/instancias" className="block px-3 py-2 rounded hover:bg-gray-800">Instancias</NavLink>
              <NavLink to="/admin/audit" className="block px-3 py-2 rounded hover:bg-gray-800">Audit log</NavLink>
            </>
          )}
        </nav>
        <button onClick={handleLogout}
          className="mt-4 text-left px-3 py-2 rounded hover:bg-gray-800 text-sm">
          Cerrar sesión
        </button>
      </aside>
      <main className="bg-gray-50 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
