<?php

declare(strict_types=1);

namespace App\Http\Controllers\Platform;

use App\Models\Application;
use App\Models\Company;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * GET /api/v1/inventory/context — Consumido por SDK de apps huésped para
 * conocer el contexto del request actual sin hardcodear (RF-062).
 *
 * Auth: ForwardAuth ya inyectó X-Auth-* headers.
 */
class InventoryContextController
{
    public function __invoke(Request $request): JsonResponse
    {
        $userId = $request->header('X-Auth-User-Id');
        $companyId = $request->header('X-Auth-Company-Id');
        $appSlug = $request->query('app');   // la app pasa su slug para obtener su licencia

        if (! $userId || ! $companyId) {
            return response()->json([
                'error' => [
                    'code' => 'AUTH_TOKEN_MISSING',
                    'message' => 'Headers X-Auth-* ausentes (debería inyectarlos ForwardAuth)',
                ],
            ], 401);
        }

        $user = User::find($userId);
        $company = Company::find($companyId);
        $app = $appSlug ? Application::where('slug', $appSlug)->first() : null;

        return response()->json([
            'data' => [
                'user' => [
                    'id' => $user?->id,
                    'email' => $user?->email,
                    'display_name' => $user?->display_name,
                ],
                'company' => [
                    'id' => $company?->id,
                    'slug' => $company?->slug,
                    'name' => $company?->name,
                ],
                'application' => $app ? [
                    'slug' => $app->slug,
                    'version' => $app->latest_version,
                ] : null,
                'maestro' => [
                    'base_domain' => config('app.base_domain'),
                    'version' => config('app.version', 'dev'),
                ],
            ],
        ]);
    }
}
