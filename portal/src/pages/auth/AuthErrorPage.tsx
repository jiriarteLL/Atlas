import { useSearchParams, Link } from 'react-router-dom';

const reasonMessages: Record<string, string> = {
  state_invalid: 'El flujo de autenticación expiró o fue alterado. Volvé a intentar.',
  provider_error: 'No pudimos contactar a Microsoft. Intentá más tarde.',
  user_not_provisioned: 'Tu cuenta de Microsoft no está autorizada. Contactá al administrador.',
  missing_token: 'El proveedor de auth no devolvió un token válido.',
};

export default function AuthErrorPage() {
  const [params] = useSearchParams();
  const reason = params.get('reason') ?? 'unknown';
  const msg = reasonMessages[reason] ?? 'Ocurrió un error al autenticar.';

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white p-8 rounded-lg shadow text-center">
        <h1 className="text-xl font-semibold mb-4">No pudimos ingresarte</h1>
        <p className="text-gray-700 mb-6">{msg}</p>
        <Link to="/login" className="text-indigo-600 hover:underline">Volver al login</Link>
      </div>
    </main>
  );
}
