<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use App\Http\Requests\Auth\LoginRequest;
use App\Models\User;
use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\ValidationException;

/**
 * Login user/pass usando OAuth2 Password Grant de Passport v13.
 *
 * Flujo:
 *   1. Validar credenciales localmente (fail-fast para audit + sin enumeración).
 *   2. Request interno a POST /oauth/token con grant_type=password.
 *   3. Passport valida y emite access_token + refresh_token firmados RS256.
 *   4. Retornar tokens y user payload.
 *
 * Requiere oauth_client con grant_types='password refresh_token', creado por DatabaseSeeder.
 * Credenciales en env: PASSPORT_PASSWORD_CLIENT_ID, PASSPORT_PASSWORD_CLIENT_SECRET.
 */
class LoginController
{
    public function __construct(
        private readonly AuditLogger $audit,
    ) {}

    public function __invoke(LoginRequest $request): JsonResponse
    {
        $email = (string) $request->string('email')->lower();
        $password = (string) $request->string('password');

        $user = User::whereNull('deleted_at')
            ->where('email', $email)
            ->first();

        // Fail-fast con mensaje genérico (T-03: no user enumeration).
        if (! $user || ! $user->password_hash || ! Hash::check($password, $user->password_hash)) {
            $this->audit->log(
                action: 'auth.login.fail',
                actorUserId: $user?->id,
                actorIp: $request->ip(),
                dataAfter: ['email' => $email],
            );
            throw ValidationException::withMessages([
                'email' => 'Email o contraseña incorrectos.',
            ])->status(401);
        }

        $clientId = env('PASSPORT_PASSWORD_CLIENT_ID');
        $clientSecret = env('PASSPORT_PASSWORD_CLIENT_SECRET');

        if (! $clientId || ! $clientSecret) {
            return response()->json([
                'error' => [
                    'code' => 'INTERNAL_ERROR',
                    'message' => 'Password Grant client no configurado. Correr `php artisan db:seed --class=PassportClientsSeeder`.',
                ],
            ], 500);
        }

        // Request interno a /oauth/token — Passport v13 emite JWT firmado
        $oauthResponse = Http::asForm()->post(url('/oauth/token'), [
            'grant_type' => 'password',
            'client_id' => $clientId,
            'client_secret' => $clientSecret,
            'username' => $email,
            'password' => $password,
            'scope' => '*',
        ]);

        if ($oauthResponse->failed()) {
            $this->audit->log(
                action: 'auth.login.oauth_fail',
                actorUserId: $user->id,
                actorIp: $request->ip(),
                dataAfter: ['status' => $oauthResponse->status()],
            );
            return response()->json([
                'error' => [
                    'code' => 'AUTH_TOKEN_INVALID',
                    'message' => 'No se pudo emitir el token.',
                    'details' => $oauthResponse->json() ?: [],
                ],
            ], 500);
        }

        $tokens = $oauthResponse->json();

        $user->last_login_at = now();
        $user->saveQuietly();

        $this->audit->log(
            action: 'auth.login.success',
            actorUserId: $user->id,
            companyId: $user->active_company_id,
            actorIp: $request->ip(),
        );

        return response()->json([
            'data' => [
                'access_token' => $tokens['access_token'],
                'refresh_token' => $tokens['refresh_token'] ?? null,
                'token_type' => $tokens['token_type'] ?? 'Bearer',
                'expires_in' => $tokens['expires_in'] ?? 3600,
                'user' => [
                    'id' => $user->id,
                    'email' => $user->email,
                    'display_name' => $user->display_name,
                    'active_company_id' => $user->active_company_id,
                    'is_platform_admin' => (bool) $user->is_platform_admin,
                ],
            ],
        ]);
    }
}
