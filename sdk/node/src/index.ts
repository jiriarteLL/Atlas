/**
 * @maestro/sdk-node — SDK oficial para apps huésped Node.js.
 */

export { loadContext } from './context.js';
export { authMiddleware, requireRole, requirePermission } from './middleware.js';
export { hookVerifierMiddleware } from './hooks.js';
export { GatewayClient } from './gateway.js';
export { tenantFilter, scopedToTenant } from './tenant.js';
export type {
  MaestroUser,
  MaestroContext,
  HookPayload,
  MaestroError,
} from './types.js';
