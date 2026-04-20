import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';

const MICROSOFT_ENABLED = import.meta.env.VITE_MICROSOFT_ENTRA_ENABLED === 'true';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const r = await api.post<{ data: { access_token: string } }>('/auth/login', { email, password });
      localStorage.setItem('maestro.access_token', r.data.data.access_token);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const maybe = err as { response?: { status?: number } };
      setError(maybe.response?.status === 401
        ? 'Email o contraseña incorrectos.'
        : 'Ocurrió un error. Intentá de nuevo.');
    } finally {
      setSubmitting(false);
    }
  }

  function handleMicrosoft() {
    window.location.href = `${import.meta.env.VITE_API_BASE_URL ?? '/api'}/auth/microsoft/redirect`;
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white p-8 rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-6 text-center">Bienvenido a Maestro</h1>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
            <input id="email" type="email" required value={email}
              data-testid="login-email"
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring focus:border-blue-500" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">Contraseña</label>
            <input id="password" type="password" required value={password}
              data-testid="login-password"
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring focus:border-blue-500" />
          </div>
          {error && <p role="alert" data-testid="login-error" className="text-red-600 text-sm">{error}</p>}
          <button type="submit" disabled={submitting}
            data-testid="login-submit"
            className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 disabled:opacity-60">
            {submitting ? 'Ingresando…' : 'Iniciar sesión'}
          </button>
        </form>

        {MICROSOFT_ENABLED && (
          <>
            <div className="my-4 text-center text-gray-500 text-sm">o</div>
            <button onClick={handleMicrosoft}
              data-testid="login-microsoft"
              className="w-full border border-gray-300 py-2 rounded hover:bg-gray-100">
              Continuar con Microsoft
            </button>
          </>
        )}
      </div>
    </main>
  );
}
