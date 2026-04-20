import { useEffect, type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuthStore, type MeUser } from '../stores/authStore';

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem('maestro.access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    api.get<{ data: MeUser }>('/auth/me')
      .then((r) => setUser(r.data.data))
      .catch(() => setUser(null));
  }, [setUser, setLoading]);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Cargando...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
