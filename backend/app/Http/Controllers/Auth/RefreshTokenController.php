<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

/**
 * Refresh token — delega al endpoint OAuth2 estándar de Passport.
 *
 * Cumple con RF-004 usando el flujo OAuth2 Refresh Grant de Laravel Passport
 * (POST /oauth/token con grant_type=refresh_token).
 */
class RefreshTokenController
{
    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'refresh_token' => ['required', 'string'],
            'client_id' => ['required', 'string'],
            'client_secret' => ['required', 'string'],
        ]);

        $response = Http::asForm()->post(url('/oauth/token'), [
            'grant_type' => 'refresh_token',
            'refresh_token' => $validated['refresh_token'],
            'client_id' => $validated['client_id'],
            'client_secret' => $validated['client_secret'],
            'scope' => '',
        ]);

        if ($response->failed()) {
            return response()->json([
                'error' => [
                    'code' => 'AUTH_TOKEN_INVALID',
                    'message' => 'refresh_token inválido o expirado',
                ],
            ], 401);
        }

        return response()->json(['data' => $response->json()]);
    }
}
