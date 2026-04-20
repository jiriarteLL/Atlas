import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
}

interface AdminTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  empty?: string;
  loading?: boolean;
}

export default function AdminTable<T extends { id: string }>({
  columns,
  rows,
  empty = 'Sin datos',
  loading = false,
}: AdminTableProps<T>) {
  if (loading) {
    return <div className="p-8 text-center text-gray-500">Cargando…</div>;
  }
  if (rows.length === 0) {
    return <div className="p-8 text-center text-gray-500">{empty}</div>;
  }
  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map(col => (
              <th key={col.key} className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map(row => (
            <tr key={row.id} className="hover:bg-gray-50">
              {columns.map(col => (
                <td key={col.key} className="px-4 py-3 text-sm text-gray-800">
                  {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
