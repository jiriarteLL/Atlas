import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import AdminTable, { type Column } from '../../components/admin/AdminTable';
import StatusBadge from '../../components/admin/StatusBadge';
import Modal from '../../components/admin/Modal';

interface Application {
  id: string;
  name: string;
  slug: string;
  latest_version: string | null;
  image_ref: string | null;
  status: string;
}

export default function ApplicationsAdminPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: '', slug: '' });

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'applications'],
    queryFn: async () => {
      const r = await api.get<{ data: Application[] }>('/admin/applications');
      return r.data.data;
    },
  });

  const createMut = useMutation({
    mutationFn: async (payload: typeof form) => api.post('/admin/applications', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'applications'] });
      setModalOpen(false);
      setForm({ name: '', slug: '' });
    },
  });

  const columns: Column<Application>[] = [
    { key: 'name', label: 'Nombre' },
    { key: 'slug', label: 'Slug' },
    {
      key: 'latest_version',
      label: 'Última versión',
      render: r => r.latest_version ?? <span className="text-gray-400">sin releases</span>,
    },
    {
      key: 'image_ref',
      label: 'Imagen',
      render: r => r.image_ref
        ? <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">{r.image_ref}</code>
        : <span className="text-gray-400">—</span>,
    },
    { key: 'status', label: 'Estado', render: r => <StatusBadge status={r.status} /> },
  ];

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createMut.mutate(form);
  }

  return (
    <div>
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Aplicaciones</h1>
          <p className="text-sm text-gray-500">Catálogo de apps disponibles para licenciar a empresas.</p>
        </div>
        <button onClick={() => setModalOpen(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">
          Nueva aplicación
        </button>
      </header>

      <AdminTable columns={columns} rows={data ?? []} loading={isLoading} empty="No hay apps en el catálogo." />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nueva aplicación"
        footer={
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded border border-gray-300 hover:bg-gray-100">Cancelar</button>
            <button onClick={handleSubmit} disabled={createMut.isPending || !form.name || !form.slug}
              className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
              {createMut.isPending ? 'Creando…' : 'Crear'}
            </button>
          </div>
        }>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nombre</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-full border rounded px-3 py-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Slug</label>
            <input value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })}
              className="w-full border rounded px-3 py-2"
              pattern="[a-z0-9][a-z0-9-]{2,49}" required />
            <p className="text-xs text-gray-500 mt-1">Imagen y versión se actualizan automáticamente con maestro-cli en cada release.</p>
          </div>
        </form>
      </Modal>
    </div>
  );
}
