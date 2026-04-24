<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

class LogoutController
{
    public function __construct(private readonly AuditLogger $audit) {}

    public function __invoke(Request $request): JsonResponse
    {
        $user = $request->user();
        $token = $user?->token();

        if ($token) {
            // Revocar token via Passport
            $token->revoke();

            // Agregar a revoked_tokens para consulta rápida durante validación
            DB::table('revoked_tokens')->insert([
                'jti' => $token->id,
                'user_id' => $user->id,
                'revoked_at' => now(),
                'expires_at' => $token->expires_at,
            ]);

            // Invalidar cache Redis
            // Nota: el bearer real no está disponible acá; el Cache::forget se hace via cache key pattern
            // en producción se invalida con tag/pattern sobre Redis.

            $this->audit->log(
                action: 'auth.logout',
                actorUserId: $user->id,
                companyId: $user->active_company_id,
                actorIp: $request->ip(),
            );
        }

        return response()->json(null, 204);
    }
}
