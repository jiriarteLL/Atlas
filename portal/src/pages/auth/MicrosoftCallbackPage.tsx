import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function MicrosoftCallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    const token = params.get('access_token');
    if (token) {
      localStorage.setItem('maestro.access_token', token);
      navigate('/', { replace: true });
    } else {
      navigate('/auth/error?reason=missing_token', { replace: true });
    }
  }, [navigate, params]);

  return <div className="flex items-center justify-center min-h-screen">Completando ingreso con Microsoft…</div>;
}
