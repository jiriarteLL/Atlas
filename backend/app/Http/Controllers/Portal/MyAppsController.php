<?php

declare(strict_types=1);

namespace App\Http\Controllers\Portal;

use App\Models\Application;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * GET /api/portal/my-apps — lista apps licenciadas del usuario
 * en su empresa activa, con estado de la instancia.
 *
 * Auth: Bearer JWT.
 */
class MyAppsController
{
    public function __invoke(Request $request): JsonResponse
    {
        $user = $request->user();
        if (! $user || ! $user->active_company_id) {
            return response()->json(['data' => []]);
        }

        $companyId = $user->active_company_id;

        // Apps licenciadas activas a la empresa activa
        $apps = Application::query()
            ->whereHas('companies', function ($q) use ($companyId) {
                $q->where('companies.id', $companyId)
                    ->where('application_company.is_active', true);
            })
            ->whereHas('users', function ($q) use ($user, $companyId) {
                $q->where('users.id', $user->id)
                    ->where('application_user.company_id', $companyId);
            })
            ->with(['companies' => fn ($q) => $q->where('companies.id', $companyId)])
            ->get();

        $baseDomain = config('app.base_domain', 'maestro.local');
        $company = $user->activeCompany;

        $data = $apps->map(function (Application $app) use ($companyId, $baseDomain, $company) {
            $license = $app->companies->firstWhere('id', $companyId)?->pivot;
            $instance = \App\Models\Instance::where('application_id', $app->id)
                ->where('company_id', $companyId)
                ->whereNull('destroyed_at')
                ->first();

            return [
                'app_id' => $app->id,
                'slug' => $app->slug,
                'name' => $app->name,
                'version' => $app->latest_version,
                'url' => "https://{$app->slug}-{$company?->subdomain}.{$baseDomain}",
                'status' => $instance?->status ?? 'not_provisioned',
                'license_active' => (bool) ($license?->is_active ?? false),
                'license_tier' => $license?->tier,
                'license_expires_at' => $license?->expires_at,
            ];
        });

        return response()->json(['data' => $data]);
    }
}
