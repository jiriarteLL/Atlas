import type { Request } from 'express';

/**
 * Helper para obtener el company_id del request autenticado.
 * Garantiza que toda query de la app se filtre por este valor.
 *
 * Uso con Knex:
 *   const companyId = tenantFilter(req);
 *   const users = await knex('users').where('company_id', companyId);
 *
 * Uso con Prisma:
 *   const companyId = tenantFilter(req);
 *   const users = await prisma.user.findMany({ where: { companyId } });
 */
export function tenantFilter(req: Request): string {
  const user = req.maestroUser;
  if (!user?.companyId) {
    throw new Error('tenantFilter called on request without auth context. Did you forget to add authMiddleware()?');
  }
  return user.companyId;
}

/**
 * Wrapper que envuelve una función async y le pasa el companyId como primer argumento.
 * Útil para encapsular queries garantizando el filtro.
 */
export function scopedToTenant<T, Args extends unknown[]>(
  fn: (companyId: string, ...args: Args) => Promise<T>,
): (req: Request, ...args: Args) => Promise<T> {
  return (req, ...args) => fn(tenantFilter(req), ...args);
}
