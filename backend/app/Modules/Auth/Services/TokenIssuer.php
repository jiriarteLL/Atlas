<?php

declare(strict_types=1);

namespace App\Modules\Auth\Services;

use App\Models\User;
use Laravel\Passport\PersonalAccessTokenResult;

/**
 * Encapsula la emisión de JWT a través de Passport + enriquecimiento del payload.
 */
class TokenIssuer
{
    public function issueForUser(User $user, ?string $companyId = null): array
    {
        /** @var PersonalAccessTokenResult $token */
        $token = $user->createToken('maestro', $this->scopesFor($user, $companyId));

        $ttlMinutes = (int) config('passport.token_lifetime_minutes', 60);

        return [
            'access_token' => $token->accessToken,
            'token_type' => 'Bearer',
            'expires_in' => $ttlMinutes * 60,
            'refresh_token' => null, // Password grant emite refresh; se añade en login via OAuth2 flow
            'user' => [
                'id' => $user->id,
                'email' => $user->email,
                'display_name' => $user->display_name,
                'active_company_id' => $companyId ?? $user->active_company_id,
                'is_platform_admin' => $user->is_platform_admin,
            ],
        ];
    }

    /**
     * Determina scopes a embeber en el JWT según el contexto.
     */
    private function scopesFor(User $user, ?string $companyId): array
    {
        $scopes = [];

        if ($user->is_platform_admin) {
            $scopes[] = 'platform:admin';
        }

        if ($companyId) {
            $scopes[] = "company:{$companyId}";
            foreach ($user->rolesInCompany($companyId) as $role) {
                $scopes[] = "role:{$role}";
            }
        }

        return $scopes;
    }
}
