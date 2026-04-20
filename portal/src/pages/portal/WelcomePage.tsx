import { useAuthStore } from '../../stores/authStore';

export default function WelcomePage() {
  const { user } = useAuthStore();
  if (!user) return null;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-2">Hola, {user.display_name}.</h1>
      <p className="text-gray-600 mb-4">
        {user.active_company
          ? `Estás operando en ${user.active_company.name}.`
          : 'Todavía no tenés una empresa activa.'}
      </p>
      <p className="text-sm text-gray-500">
        Las aplicaciones licenciadas aparecerán a la izquierda una vez que el admin te asigne acceso.
      </p>
    </div>
  );
}
