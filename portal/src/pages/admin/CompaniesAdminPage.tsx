import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import AdminTable, { type Column } from '../../components/admin/AdminTable';
import StatusBadge from '../../components/admin/StatusBadge';
import Modal from '../../components/admin/Modal';

interface Company {
  id: string;
  name: string;
  slug: string;
  subdomain: string;
  status: string;
  created_at: string;
}

export default function CompaniesAdminPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: '', slug: '', subdomain: '' });
  const [formError, setFormError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'companies'],
    queryFn: async () => {
      const r = await api.get<{ data: Company[] }>('/admin/companies');
      return r.data.data;
    },
  });

  const createMut = useMutation({
    mutationFn: async (payload: typeof form) => {
      const r = await api.post('/admin/companies', payload);
      return r.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'companies'] });
      setModalOpen(false);
      setForm({ name: '', slug: '', subdomain: '' });
      setFormError(null);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        .response?.data?.error?.message ?? 'Error al crear empresa';
      setFormError(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/admin/companies/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'companies'] }),
  });

  const columns: Column<Company>[] = [
    { key: 'name', label: 'Nombre' },
    { key: 'slug', label: 'Slug' },
    { key: 'subdomain', label: 'Subdominio' },
    { key: 'status', label: 'Estado', render: r => <StatusBadge status={r.status} /> },
    {
      key: 'created_at',
      label: 'Creada',
      render: r => new Date(r.created_at).toLocaleDateString('es-AR'),
    },
    {
      key: 'actions',
      label: '',
      render: r => (
        <button
          onClick={() => {
            if (confirm(`¿Eliminar empresa ${r.name}? (soft delete, 90 días para restaurar)`)) {
              deleteMut.mutate(r.id);
            }
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

  function autoSlug(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
  }

  return (
    <div>
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Empresas</h1>
          <p className="text-sm text-gray-500">Tenants registrados en la plataforma.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Nueva empresa
        </button>
      </header>

      <AdminTable
        columns={columns}
        rows={data ?? []}
        loading={isLoading}
        empty="No hay empresas cargadas. Creá la primera."
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nueva empresa"
        footer={
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded border border-gray-300 hover:bg-gray-100"
              disabled={createMut.isPending}
            >
              Cancelar
            </button>
            <button
              onClick={handleSubmit}
              disabled={createMut.isPending || !form.name}
              className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {createMut.isPending ? 'Creando…' : 'Crear'}
            </button>
          </div>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nombre</label>
            <input
              value={form.name}
              onChange={e => {
                const name = e.target.value;
                const slug = form.slug || autoSlug(name);
                setForm({ ...form, name, slug, subdomain: form.subdomain || slug });
              }}
              className="w-full border rounded px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Slug</label>
            <input
              value={form.slug}
              onChange={e => setForm({ ...form, slug: e.target.value })}
              className="w-full border rounded px-3 py-2"
              pattern="[a-z0-9][a-z0-9-]{1,48}[a-z0-9]"
              required
            />
            <p className="text-xs text-gray-500 mt-1">Minúsculas, números y guiones. 3-50 caracteres.</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subdominio</label>
            <input
              value={form.subdomain}
              onChange={e => setForm({ ...form, subdomain: e.target.value })}
              className="w-full border rounded px-3 py-2"
              pattern="[a-z0-9][a-z0-9-]{1,48}[a-z0-9]"
              required
            />
          </div>
          {formError && <p className="text-red-600 text-sm">{formError}</p>}
        </form>
      </Modal>
    </div>
  );
}
