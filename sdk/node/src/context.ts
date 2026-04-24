import type { MaestroContext } from './types.js';

/**
 * Lee el contexto de la app desde env vars inyectadas por el Maestro.
 * Lanza si alguna var obligatoria falta.
 */
export function loadContext(): MaestroContext {
  const require = (name: string): string => {
    const v = process.env[name];
    if (!v) throw new Error(`Missing required env var: ${name}`);
    return v;
  };

  return {
    appId: require('MAESTRO_APP_ID'),
    appSlug: require('MAESTRO_APP_SLUG'),
    companyId: require('MAESTRO_COMPANY_ID'),
    companySlug: require('MAESTRO_COMPANY_SLUG'),
    instanceId: require('MAESTRO_INSTANCE_ID'),
    baseUrl: require('MAESTRO_BASE_URL'),
    gatewayUrl: require('MAESTRO_GATEWAY_URL'),
    jwksUrl: require('MAESTRO_JWKS_URL'),
    webhookSecret: require('MAESTRO_WEBHOOK_SECRET'),
  };
}
