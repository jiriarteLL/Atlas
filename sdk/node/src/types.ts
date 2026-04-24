/**
 * Tipos públicos del SDK @maestro/sdk-node.
 */

/** Identidad del usuario autenticado, construida desde headers X-Auth-*. */
export interface MaestroUser {
  id: string;
  email: string;
  companyId: string;
  roles: string[];
  permissions: string[];
}

/** Contexto inyectado por el Maestro via env vars al contenedor de la app huésped. */
export interface MaestroContext {
  appId: string;
  appSlug: string;
  companyId: string;
  companySlug: string;
  instanceId: string;
  baseUrl: string;
  gatewayUrl: string;
  jwksUrl: string;
  webhookSecret: string;
}

/** Payload del hook on_user_added / on_user_removed firmado con HMAC. */
export interface HookPayload<T = unknown> {
  event_type: string;
  delivery_id: string;
  timestamp: string;
  company_id: string;
  data: T;
}

/** Error estándar Maestro. */
export interface MaestroError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

declare global {
  namespace Express {
    interface Request {
      maestroUser?: MaestroUser;
    }
  }
}
