<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class MeController
{
    public function __invoke(Request $request): JsonResponse
    {
        $user = $request->user();

        return response()->json([
            'data' => [
                'id' => $user->id,
                'email' => $user->email,
                'display_name' => $user->display_name,
                'is_platform_admin' => (bool) $user->is_platform_admin,
                'active_company' => $user->activeCompany?->only(['id', 'name', 'slug']),
                'companies' => $user->companies()->get(['companies.id', 'name', 'slug', 'subdomain'])
                    ->map(fn ($c) => [
                        'id' => $c->id,
                        'name' => $c->name,
                        'slug' => $c->slug,
                        'subdomain' => $c->subdomain,
                        'roles' => is_array($c->pivot->roles) ? $c->pivot->roles : (json_decode($c->pivot->roles ?? '[]', true) ?: []),
                        'is_active' => (bool) $c->pivot->is_active,
                    ]),
                'roles_in_active_company' => $user->active_company_id
                    ? $user->rolesInCompany($user->active_company_id) : [],
                'permissions_in_active_company' => $user->active_company_id
                    ? $user->permissionsInCompany($user->active_company_id) : [],
            ],
        ]);
    }
}
