import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import AdminTable, { type Column } from '../../components/admin/AdminTable';
import Modal from '../../components/admin/Modal';

interface User {
  id: string;
  email: string;
  display_name: string;
  is_platform_admin: boolean;
  active_company_id: string | null;
  has_password: boolean;
  has_microsoft_link: boolean;
  last_login_at: string | null;
}

export default function UsersAdminPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    email: '',
    display_name: '',
    password: '',
    is_platform_admin: false,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const r = await api.get<{ data: User[] }>('/admin/users');
      return r.data.data;
    },
  });

  const createMut = useMutation({
    mutationFn: async (payload: typeof form) => api.post('/admin/users', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] });
      setModalOpen(false);
      setForm({ email: '', display_name: '', password: '', is_platform_admin: false });
      setFormError(null);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        .response?.data?.error?.message ?? 'Error al crear usuario';
      setFormError(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });

  const columns: Column<User>[] = [
    { key: 'email', label: 'Email' },
    { key: 'display_name', label: 'Nombre' },
    {
      key: 'is_platform_admin',
      label: 'Tipo',
      render: r => (
        <span className={r.is_platform_admin ? 'text-indigo-600 font-medium' : 'text-gray-600'}>
          {r.is_platform_admin ? 'Platform Admin' : 'Usuario'}
        </span>
      ),
    },
    {
      key: 'auth',
      label: 'Auth',
      render: r => (
        <div className="flex gap-1 text-xs">
          {r.has_password && <span className="bg-gray-200 px-1 rounded">pass</span>}
          {r.has_microsoft_link && <span className="bg-blue-200 px-1 rounded">MS</span>}
        </div>
      ),
    },
    {
      key: 'last_login_at',
      label: 'Último login',
      render: r => r.last_login_at ? new Date(r.last_login_at).toLocaleString('es-AR') : 'Nunca',
    },
    {
      key: 'actions',
      label: '',
      render: r => (
        <button
          onClick={() => {
            if (confirm(`¿Eliminar usuario ${r.email}?`)) deleteMut.mutate(r.id);
          }}
          className="text-red-600 hover:underline text-xs"
        >
          Eliminar
        </button>
      ),
    },
  ];

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createMut.mutate(form);
  }

  return (
    <div>
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Usuarios</h1>
          <p className="text-sm text-gray-500">Todos los usuarios del Maestro.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Nuevo usuario
        </button>
      </header>

      <AdminTable columns={columns} rows={data ?? []} loading={isLoading} empty="No hay usuarios." />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nuevo usuario"
        footer={
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded border border-gray-300 hover:bg-gray-100">Cancelar</button>
            <button onClick={handleSubmit} disabled={createMut.isPending || !form.email}
              className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
              {createMut.isPending ? 'Creando…' : 'Crear'}
            </button>
          </div>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              className="w-full border rounded px-3 py-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Nombre</label>
            <input value={form.display_name}
              onChange={e => setForm({ ...form, display_name: e.target.value })}
              className="w-full border rounded px-3 py-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Contraseña (opcional; mínimo 12 chars)</label>
            <input type="password" value={form.password} minLength={12}
              onChange={e => setForm({ ...form, password: e.target.value })}
              className="w-full border rounded px-3 py-2"
              placeholder="Dejar vacío para solo Microsoft Login" />
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_platform_admin}
              onChange={e => setForm({ ...form, is_platform_admin: e.target.checked })} />
            <span>Platform Admin (acceso total a admin API)</span>
          </label>
          {formError && <p className="text-red-600 text-sm">{formError}</p>}
        </form>
      </Modal>
    </div>
  );
}
