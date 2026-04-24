<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Previene cross-tenant data leak (T-01 del threat model).
 * Si la request incluye `company_id` en el body, verifica que coincida con el
 * company_id del usuario autenticado (X-Auth-Company-Id).
 */
class EnforceCompanyIdFilter
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();
        $activeCompanyId = $user?->active_company_id;

        // Rechazar si el body pasa un company_id distinto al activo
        $bodyCompanyId = $request->input('company_id');
        if ($bodyCompanyId && $activeCompanyId && $bodyCompanyId !== $activeCompanyId) {
            return response()->json([
                'error' => [
                    'code' => 'AUTH_COMPANY_MISMATCH',
                    'message' => 'company_id en body no coincide con empresa activa',
                ],
            ], 403);
        }

        return $next($request);
    }
}
