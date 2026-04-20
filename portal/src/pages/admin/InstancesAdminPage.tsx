import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import AdminTable, { type Column } from '../../components/admin/AdminTable';
import StatusBadge from '../../components/admin/StatusBadge';

interface Instance {
  id: string;
  application_id: string;
  company_id: string;
  status: string;
  image_ref: string;
  resources_memory: string;
  resources_cpu: string;
  last_healthy_at: string | null;
  provisioned_at: string | null;
  application?: { slug: string; name: string };
  company?: { slug: string; name: string };
}

export default function InstancesAdminPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'instances'],
    queryFn: async () => {
      const r = await api.get<{ data: Instance[] }>('/admin/instances');
      return r.data.data;
    },
    refetchInterval: 15_000, // refresh cada 15s para ver cambios de estado
  });

  const actionMut = useMutation({
    mutationFn: async (vars: { id: string; action: 'stop' | 'start' | 'restart' | 'destroy' }) => {
      if (vars.action === 'destroy') {
        return api.delete(`/admin/instances/${vars.id}`);
      }
      return api.post(`/admin/instances/${vars.id}/${vars.action}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'instances'] }),
  });

  const columns: Column<Instance>[] = [
    {
      key: 'company',
      label: 'Empresa',
      render: r => r.company?.name ?? r.company_id.slice(0, 8),
    },
    {
      key: 'application',
      label: 'App',
      render: r => r.application?.name ?? r.application_id.slice(0, 8),
    },
    { key: 'status', label: 'Estado', render: r => <StatusBadge status={r.status} /> },
    {
      key: 'resources',
      label: 'Recursos',
      render: r => `${r.resources_memory} · ${r.resources_cpu} CPU`,
    },
    {
      key: 'last_healthy_at',
      label: 'Última OK',
      render: r => r.last_healthy_at
        ? new Date(r.last_healthy_at).toLocaleString('es-AR')
        : <span className="text-gray-400">nunca</span>,
    },
    {
      key: 'actions',
      label: 'Acciones',
      render: r => (
        <div className="flex gap-2 text-xs">
          {r.status === 'healthy' || r.status === 'degraded' ? (
            <button onClick={() => actionMut.mutate({ id: r.id, action: 'stop' })}
              className="text-yellow-700 hover:underline">Detener</button>
          ) : r.status === 'suspended' ? (
            <button onClick={() => actionMut.mutate({ id: r.id, action: 'start' })}
              className="text-green-700 hover:underline">Iniciar</button>
          ) : null}
          {r.status !== 'destroyed' && r.status !== 'purged' && (
            <>
              <button onClick={() => actionMut.mutate({ id: r.id, action: 'restart' })}
                className="text-blue-700 hover:underline">Reiniciar</button>
              <button
                onClick={() => {
                  if (confirm('Esta acción marca la instancia como destroyed. Los datos se retienen 90 días.')) {
                    actionMut.mutate({ id: r.id, action: 'destroy' });
                  }
                }}
                className="text-red-700 hover:underline">Destruir</button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Instancias</h1>
        <p className="text-sm text-gray-500">Estado en tiempo real de las apps provisionadas.</p>
      </header>

      <AdminTable
        columns={columns}
        rows={data ?? []}
        loading={isLoading}
        empty="No hay instancias provisionadas. Provisioná una desde detalle de licencia."
      />
    </div>
  );
}
