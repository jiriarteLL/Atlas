import express from 'express';
import {
  authMiddleware,
  hookVerifierMiddleware,
  tenantFilter,
} from '@maestro/sdk-node';

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));

// --- Health check público (obligatorio, no-negociable 3) ---
app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

// --- Hooks salientes del Maestro (verificados HMAC) ---
app.post('/hooks/user-added', hookVerifierMiddleware(), (req, res) => {
  console.log('User added:', req.body);
  // Implementar lógica: crear perfil local, asignar permisos default, etc.
  res.status(200).json({ received: true });
});

app.post('/hooks/user-removed', hookVerifierMiddleware(), (req, res) => {
  console.log('User removed:', req.body);
  // Implementar lógica: soft-delete datos del usuario en la app.
  res.status(200).json({ received: true });
});

// --- Rutas protegidas por ForwardAuth ---
app.use(authMiddleware());

app.get('/api/hello', (req, res) => {
  const companyId = tenantFilter(req);
  res.json({
    message: `Hola ${req.maestroUser?.email}`,
    companyId,
  });
});

const port = Number(process.env.PORT ?? process.env.APP_PORT ?? 3000);
app.listen(port, () => {
  console.log(`{{APP_NAME}} escuchando en :${port}`);
});
