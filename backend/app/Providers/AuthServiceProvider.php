<?php

declare(strict_types=1);

namespace App\Providers;

use Illuminate\Foundation\Support\Providers\AuthServiceProvider as ServiceProvider;
use Laravel\Passport\Passport;

class AuthServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        // Passport: TTLs y claves (ADR-001, T-06)
        Passport::tokensExpireIn(
            now()->addMinutes((int) config('passport.token_lifetime_minutes', 60))
        );
        Passport::refreshTokensExpireIn(
            now()->addDays((int) config('passport.refresh_token_lifetime_days', 30))
        );
        Passport::personalAccessTokensExpireIn(now()->addDays(30));

        // Passport v13: habilitar explícitamente Password Grant (desabilitado por default)
        if (method_exists(Passport::class, 'enablePasswordGrant')) {
            Passport::enablePasswordGrant();
        }

        // Microsoft Entra ID: flujo implementado directo en MicrosoftController
        // (sin dep de provider Socialite externo por conflictos de compat PHP 8.3).
    }
}
