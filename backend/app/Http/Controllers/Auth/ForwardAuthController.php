<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Laravel\Passport\Token;

/**
 * Endpoint consumido por Traefik ForwardAuth middleware (RF-003, RNF-001).
 *
 * Valida el JWT recibido en Authorization y, si es válido:
 *   - 200 OK con headers X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id,
 *     X-Auth-Roles, X-Auth-Permissions.
 *   - 401 si el token no es válido, expiró o fue revocado.
 *
 * SLA objetivo: p95 < 50ms. Cache Redis de 300s por token (RNF-003).
 */
class ForwardAuthController
{
    public function __invoke(Request $request): Response
    {
        $bearer = $this->extractBearer($request);
        if (! $bearer) {
            return response('', 401);
        }

        $cacheKey = 'token:'.hash('sha256', $bearer);
        $ttl = (int) config('passport.token_cache_ttl_seconds', 300);

        $payload = Cache::remember($cacheKey, $ttl, function () {
            // Valida el token via Passport (RS256 strict). Usar auth('api') directo
            // para evitar recursión infinita con el request resolver.
            $user = auth('api')->user();
            if (! $user) {
                return null;
            }

            // Verificar que no esté revocado (revoked_tokens tabla)
            $token = method_exists($user, 'token') ? $user->token() : null;
            if ($token && DB::table('revoked_tokens')->where('jti', $token->id)->exists()) {
                return null;
            }

            return [
                'user_id' => $user->id,
                'email' => $user->email,
                'company_id' => (string) ($user->active_company_id ?? ''),
                'roles' => $user->active_company_id
                    ? $user->rolesInCompany($user->active_company_id)
                    : [],
                'permissions' => $user->active_company_id
                    ? $user->permissionsInCompany($user->active_company_id)
                    : [],
            ];
        });

        if (! $payload) {
            Cache::forget($cacheKey);   // invalidar cache negativa
            return response('', 401);
        }

        return response('', 200)
            ->header('X-Auth-User-Id', $payload['user_id'])
            ->header('X-Auth-User-Email', $payload['email'])
            ->header('X-Auth-Company-Id', $payload['company_id'])
            ->header('X-Auth-Roles', implode(',', $payload['roles']))
            ->header('X-Auth-Permissions', implode(',', $payload['permissions']));
    }

    private function extractBearer(Request $request): ?string
    {
        $header = $request->header('Authorization', '');
        if (! is_string($header) || ! preg_match('/Bearer\s+(.+)/i', $header, $m)) {
            return null;
        }
        return trim($m[1]);
    }
}
