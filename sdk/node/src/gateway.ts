import { loadContext } from './context.js';
import type { MaestroUser } from './types.js';

/**
 * Cliente del Gateway inter-apps. Permite que una app huésped llame a otra
 * del mismo tenant via el endpoint `/api/v1/gateway/{target_app}/{path}` del Maestro.
 *
 * El usuario originador debe tener el permiso `gateway:{target_app}`.
 */
export class GatewayClient {
  private readonly ctx = loadContext();

  constructor(private readonly user: MaestroUser) {}

  async call<T = unknown>(
    targetApp: string,
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    const url = `${this.ctx.gatewayUrl.replace(/\/$/, '')}/${targetApp}${path.startsWith('/') ? path : '/' + path}`;

    const response = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-User-Id': this.user.id,
        'X-Auth-User-Email': this.user.email,
        'X-Auth-Company-Id': this.user.companyId,
        'X-Auth-Roles': this.user.roles.join(','),
        'X-Auth-Permissions': this.user.permissions.join(','),
        ...init.headers,
      },
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Gateway call to ${targetApp} failed: ${response.status} ${body}`);
    }

    const contentType = response.headers.get('Content-Type') ?? '';
    if (contentType.includes('application/json')) {
      return (await response.json()) as T;
    }
    return (await response.text()) as unknown as T;
  }
}
