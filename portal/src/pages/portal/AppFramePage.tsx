import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

type AppState = 'loading' | 'cold-start' | 'ready' | 'error';

export default function AppFramePage() {
  const { slug } = useParams();
  const { user } = useAuthStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<AppState>('loading');
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!slug || !user?.active_company) return;
    // Construcción del subdominio: <slug>-<company>.<base_domain>
    // Por ahora: placeholder URL — en iteración siguiente se consulta a /api/portal/my-apps
    setState('cold-start');
    const start = Date.now();
    const tick = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    // Simulación: pasar a ready tras 2s. La iteración siguiente implementa el polling real.
    const ready = setTimeout(() => setState('ready'), 2000);
    return () => { clearInterval(tick); clearTimeout(ready); };
  }, [slug, user?.active_company]);

  useEffect(() => {
    function handleMessage(e: MessageEvent) {
      // Solo aceptar mensajes del iframe esperado
      if (!iframeRef.current) return;
      if (e.source !== iframeRef.current.contentWindow) return;
      if (e.data?.type === 'maestro:ready') setState('ready');
    }
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  if (!user?.active_company) return <p>Sin empresa activa.</p>;

  if (state === 'cold-start') {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="text-3xl mb-4">🔄</div>
        <h2 className="text-lg font-semibold mb-2">Iniciando aplicación…</h2>
        <p className="text-sm text-gray-500">Tiempo transcurrido: {elapsed}s (estimado &lt; 15s)</p>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="text-center">
        <h2 className="text-lg font-semibold mb-2">No pudimos cargar la aplicación.</h2>
        <button onClick={() => setState('cold-start')} className="text-indigo-600 hover:underline">
          Reintentar
        </button>
      </div>
    );
  }

  const baseDomain = import.meta.env.VITE_API_BASE_URL?.includes('localhost') ? 'maestro.local' : 'maestro.local';
  const src = `https://${slug}-${user.active_company.slug}.${baseDomain}`;

  return (
    <iframe
      ref={iframeRef}
      title={`Maestro app ${slug}`}
      src={src}
      sandbox="allow-forms allow-scripts allow-same-origin allow-popups allow-top-navigation-by-user-activation"
      className="w-full h-[calc(100vh-3rem)] border-0 bg-white rounded shadow"
    />
  );
}
