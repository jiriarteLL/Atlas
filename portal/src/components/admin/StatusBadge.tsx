import clsx from 'clsx';

const variants: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  healthy: 'bg-green-100 text-green-800',
  starting: 'bg-blue-100 text-blue-800',
  provisioning: 'bg-blue-100 text-blue-800',
  degraded: 'bg-yellow-100 text-yellow-800',
  suspended: 'bg-gray-200 text-gray-800',
  destroyed: 'bg-red-100 text-red-800',
  failed: 'bg-red-100 text-red-800',
  inactive: 'bg-gray-200 text-gray-600',
  deprecated: 'bg-yellow-100 text-yellow-800',
  retired: 'bg-red-100 text-red-800',
};

export default function StatusBadge({ status }: { status: string | null | undefined }) {
  const key = (status ?? 'inactive').toLowerCase();
  const cls = variants[key] ?? 'bg-gray-100 text-gray-700';
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', cls)}>
      {status ?? '—'}
    </span>
  );
}
