import type { NextFunction, Request, Response } from 'express';
import type { MaestroUser } from './types.js';

/**
 * Middleware Express que lee los headers X-Auth-* inyectados por Traefik ForwardAuth
 * y popula `req.maestroUser`. Si faltan los obligatorios, responde 401.
 *
 * Uso:
 *   import { authMiddleware } from '@maestro/sdk-node';
 *   app.use(authMiddleware());
 */
export function authMiddleware() {
  return (req: Request, res: Response, next: NextFunction) => {
    const userId = req.header('X-Auth-User-Id');
    const email = req.header('X-Auth-User-Email');
    const companyId = req.header('X-Auth-Company-Id');

    if (!userId || !companyId) {
      res.status(401).json({
        error: {
          code: 'AUTH_TOKEN_MISSING',
          message: 'Headers X-Auth-User-Id o X-Auth-Company-Id ausentes (la request no pasó por ForwardAuth).',
        },
      });
      return;
    }

    const rolesHeader = req.header('X-Auth-Roles') ?? '';
    const permissionsHeader = req.header('X-Auth-Permissions') ?? '';

    const user: MaestroUser = {
      id: userId,
      email: email ?? '',
      companyId,
      roles: rolesHeader ? rolesHeader.split(',').map(r => r.trim()).filter(Boolean) : [],
      permissions: permissionsHeader ? permissionsHeader.split(',').map(p => p.trim()).filter(Boolean) : [],
    };

    req.maestroUser = user;
    next();
  };
}

/**
 * Helper que requiere que el user tenga uno de los roles dados. 403 si no.
 */
export function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = req.maestroUser;
    if (!user) {
      res.status(401).json({ error: { code: 'AUTH_TOKEN_MISSING', message: 'No auth context.' } });
      return;
    }
    const hasRole = user.roles.includes('*') || roles.some(r => user.roles.includes(r));
    if (!hasRole) {
      res.status(403).json({
        error: {
          code: 'PERMISSION_DENIED',
          message: `Requiere uno de los roles: ${roles.join(', ')}`,
        },
      });
      return;
    }
    next();
  };
}

/**
 * Helper que requiere un permiso específico (o wildcard *).
 */
export function requirePermission(permission: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = req.maestroUser;
    if (!user) {
      res.status(401).json({ error: { code: 'AUTH_TOKEN_MISSING', message: 'No auth context.' } });
      return;
    }
    const hasPerm = user.permissions.includes('*') || user.permissions.includes(permission);
    if (!hasPerm) {
      res.status(403).json({
        error: {
          code: 'PERMISSION_DENIED',
          message: `Requiere permiso: ${permission}`,
        },
      });
      return;
    }
    next();
  };
}
