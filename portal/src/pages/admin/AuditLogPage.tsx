import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

interface AuditEntry {
  id: number;
  at: string;
  actor_user_id: string | null;
  company_id: string | null;
  actor_ip: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  data_before: Record<string, unknown> | null;
  data_after: Record<string, unknown> | null;
}

export default function AuditLogPage() {
  const [filter, setFilter] = useState('');
  const [expanded, setExpanded] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'audit-log'],
    queryFn: async () => {
      const r = await api.get<{ data: AuditEntry[] }>('/admin/audit-log', { params: { per_page: 100 } });
      return r.data.data;
    },
    refetchInterval: 10_000,
  });

  const filtered = (data ?? []).filter(
    e => !filter
      || e.action.toLowerCase().includes(filter.toLowerCase())
      || (e.actor_user_id ?? '').includes(filter)
      || (e.resource_type ?? '').includes(filter),
  );

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <p className="text-sm text-gray-500">
          Histórico inmutable de todas las acciones administrativas. INSERT-only a nivel BD.
        </p>
      </header>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Filtrar por acción, user o recurso…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="w-full max-w-md border rounded px-3 py-2"
        />
      </div>

      {isLoading ? (
        <p className="text-gray-500">Cargando…</p>
      ) : (
        <div className="space-y-2">
          {filtered.map(entry => (
            <div key={entry.id} className="border border-gray-200 rounded bg-white p-3 text-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 font-mono">
                    {new Date(entry.at).toLocaleString('es-AR')}
                  </span>
                  <code className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-xs">
                    {entry.action}
                  </code>
                  {entry.resource_type && (
                    <span className="text-gray-600 text-xs">
                      {entry.resource_type}
                      {entry.resource_id ? `/${entry.resource_id.slice(0, 8)}` : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{entry.actor_ip ?? '—'}</span>
                  <button
                    onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                    className="text-indigo-600 hover:underline"
                  >
                    {expanded === entry.id ? 'ocultar' : 'ver diff'}
                  </button>
                </div>
              </div>

              {expanded === entry.id && (
                <div className="mt-3 grid grid-cols-2 gap-4 pt-3 border-t">
                  <div>
                    <div className="text-xs font-semibold text-gray-500 mb-1">Antes</div>
                    <pre className="bg-red-50 text-red-900 p-2 rounded text-xs overflow-x-auto">
                      {JSON.stringify(entry.data_before ?? null, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-gray-500 mb-1">Después</div>
                    <pre className="bg-green-50 text-green-900 p-2 rounded text-xs overflow-x-auto">
                      {JSON.stringify(entry.data_after ?? null, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-gray-500 text-center p-8">Sin resultados para este filtro.</p>
          )}
        </div>
      )}
    </div>
  );
}
