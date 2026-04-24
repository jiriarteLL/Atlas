<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use App\Models\User;
use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Auth\Services\TokenIssuer;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response as SymfonyResponse;

/**
 * Flujo OAuth2 con Microsoft Entra ID implementado con HTTP directo
 * contra el endpoint /oauth2/v2.0/ del tenant. Sin dependencia de
 * provider Socialite externo (evita conflictos de versión de PHP).
 *
 * Mitigaciones de threat model:
 *   - T-04 (CSRF state hijack): state random 32+ + nonce OIDC en cache Redis 5min.
 *   - T-03 (robo de token): redirect con access_token en query es temporal; el portal lo
 *     mueve inmediatamente a localStorage. Opción más segura (cookie httpOnly server-side)
 *     se implementa en iteración siguiente.
 */
class MicrosoftController
{
    public function __construct(
        private readonly TokenIssuer $issuer,
        private readonly AuditLogger $audit,
    ) {}

    public function redirect(Request $request): RedirectResponse|JsonResponse
    {
        if ($guard = $this->guardDisabled($request, 'auth.microsoft.redirect.fail')) {
            return $guard;
        }

        $state = Str::random(40);
        $nonce = Str::random(32);
        Cache::put("oauth_state:{$state}", [
            'at' => now()->toIso8601String(),
            'nonce' => $nonce,
        ], now()->addMinutes(5));

        $tenant = (string) config('services.microsoft.tenant', 'common');
        $clientId = (string) config('services.microsoft.client_id');
        $redirectUri = (string) config('services.microsoft.redirect');

        $params = http_build_query([
            'client_id' => $clientId,
            'response_type' => 'code',
            'redirect_uri' => $redirectUri,
            'response_mode' => 'query',
            'scope' => 'openid profile email offline_access User.Read',
            'state' => $state,
            'nonce' => $nonce,
        ]);

        return redirect()->away(
            "https://login.microsoftonline.com/{$tenant}/oauth2/v2.0/authorize?{$params}"
        );
    }

    public function callback(Request $request): RedirectResponse|JsonResponse
    {
        if ($guard = $this->guardDisabled($request, 'auth.microsoft.callback.fail')) {
            return $guard;
        }

        $portalUrl = rtrim((string) config('app.maestro_portal_url', config('app.url')), '/');
        $state = (string) $request->query('state', '');
        $code = (string) $request->query('code', '');

        $cached = $state ? Cache::pull("oauth_state:{$state}") : null;
        if (! $cached || ! $code) {
            $this->audit->log('auth.microsoft.callback.fail', actorIp: $request->ip(),
                dataAfter: ['reason' => 'state_invalid']);
            return redirect()->to("{$portalUrl}/auth/error?reason=state_invalid");
        }

        $tenant = (string) config('services.microsoft.tenant', 'common');

        // Intercambiar code por tokens
        $tokenRes = Http::asForm()->post(
            "https://login.microsoftonline.com/{$tenant}/oauth2/v2.0/token",
            [
                'client_id' => config('services.microsoft.client_id'),
                'client_secret' => config('services.microsoft.client_secret'),
                'code' => $code,
                'redirect_uri' => config('services.microsoft.redirect'),
                'grant_type' => 'authorization_code',
            ]
        );

        if ($tokenRes->failed()) {
            $this->audit->log('auth.microsoft.callback.fail', actorIp: $request->ip(),
                dataAfter: ['reason' => 'token_exchange_failed']);
            return redirect()->to("{$portalUrl}/auth/error?reason=provider_error");
        }

        $tokens = $tokenRes->json();

        // Obtener userinfo desde Microsoft Graph
        $userinfoRes = Http::withToken($tokens['access_token'])
            ->get('https://graph.microsoft.com/oidc/userinfo');

        if ($userinfoRes->failed()) {
            $this->audit->log('auth.microsoft.callback.fail', actorIp: $request->ip(),
                dataAfter: ['reason' => 'userinfo_failed']);
            return redirect()->to("{$portalUrl}/auth/error?reason=provider_error");
        }

        $info = $userinfoRes->json();
        $sub = (string) ($info['sub'] ?? '');
        $email = strtolower((string) ($info['email'] ?? $info['preferred_username'] ?? ''));
        $name = (string) ($info['name'] ?? $email);

        if (! $sub || ! $email) {
            return redirect()->to("{$portalUrl}/auth/error?reason=provider_error");
        }

        $user = User::where('entra_id_sub', $sub)
            ->orWhere('email', $email)
            ->first();

        if (! $user) {
            if (! config('services.microsoft.auto_provision', false)) {
                $this->audit->log('auth.microsoft.callback.fail', actorIp: $request->ip(),
                    dataAfter: ['reason' => 'user_not_provisioned', 'email' => $email]);
                return redirect()->to("{$portalUrl}/auth/error?reason=user_not_provisioned");
            }
            $user = User::create([
                'email' => $email,
                'entra_id_sub' => $sub,
                'display_name' => $name,
                'is_platform_admin' => false,
            ]);
        } elseif (! $user->entra_id_sub) {
            $user->entra_id_sub = $sub;
            $user->saveQuietly();
        }

        $user->last_login_at = now();
        $user->saveQuietly();

        $payload = $this->issuer->issueForUser($user, $user->active_company_id);

        $this->audit->log(
            action: 'auth.microsoft.login.success',
            actorUserId: $user->id,
            companyId: $user->active_company_id,
            actorIp: $request->ip(),
        );

        return redirect()->to("{$portalUrl}/auth/callback?access_token=".urlencode($payload['access_token']));
    }

    /**
     * Si MICROSOFT_ENTRA_ENABLED=false, corta el flujo con 503 y audita el intento.
     * DEC-026 (stabilization-1): Entra ID queda tras feature flag para entornos sin credenciales reales.
     */
    private function guardDisabled(Request $request, string $auditAction): ?JsonResponse
    {
        if (config('services.microsoft.enabled') === true) {
            return null;
        }

        $this->audit->log($auditAction, actorIp: $request->ip(),
            dataAfter: ['reason' => 'entra_disabled']);

        return response()->json([
            'error' => [
                'code' => 'entra_disabled',
                'message' => 'La federación con Microsoft Entra ID está deshabilitada en este entorno.',
            ],
        ], SymfonyResponse::HTTP_SERVICE_UNAVAILABLE);
    }
}
