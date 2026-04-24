import crypto from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';
import { loadContext } from './context.js';

/**
 * Middleware que verifica la firma HMAC-SHA256 de hooks entrantes del Maestro.
 *
 * El Maestro firma: body raw con MAESTRO_WEBHOOK_SECRET.
 * La app espera header: X-Maestro-Webhook-Secret: <hmac hex>
 *
 * También rechaza replays: delivery_id repetido en los últimos 5 min (a nivel app, opcional).
 *
 * Uso:
 *   app.post('/hooks/user-added', hookVerifierMiddleware(), async (req, res) => { ... });
 */
export function hookVerifierMiddleware(opts: { windowSeconds?: number } = {}) {
  const windowSeconds = opts.windowSeconds ?? 300;
  const ctx = loadContext();

  return (req: Request, res: Response, next: NextFunction) => {
    const received = req.header('X-Maestro-Webhook-Secret');
    if (!received) {
      res.status(401).json({ error: { code: 'AUTH_TOKEN_MISSING', message: 'Missing X-Maestro-Webhook-Secret' } });
      return;
    }

    // body raw — asume express.raw() en la ruta, o JSON body stringificado.
    const body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body ?? {});
    const expected = crypto
      .createHmac('sha256', ctx.webhookSecret)
      .update(body)
      .digest('hex');

    const valid = crypto.timingSafeEqual(
      Buffer.from(received.padEnd(64, '0').slice(0, 64)),
      Buffer.from(expected.padEnd(64, '0').slice(0, 64)),
    );

    if (!valid) {
      res.status(401).json({ error: { code: 'AUTH_TOKEN_INVALID', message: 'HMAC signature mismatch' } });
      return;
    }

    // Anti-replay por timestamp
    const tsHeader = req.header('X-Maestro-Delivery-Timestamp');
    if (tsHeader) {
      const ts = parseInt(tsHeader, 10);
      const nowSec = Math.floor(Date.now() / 1000);
      if (Number.isFinite(ts) && Math.abs(nowSec - ts) > windowSeconds) {
        res.status(401).json({
          error: { code: 'AUTH_TOKEN_EXPIRED', message: `Hook timestamp fuera de ventana ${windowSeconds}s` },
        });
        return;
      }
    }

    next();
  };
}
