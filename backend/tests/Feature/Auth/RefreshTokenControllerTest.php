<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class RefreshTokenControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_refresh_requiere_campos(): void
    {
        $this->postJson('/api/auth/refresh', [])
            ->assertStatus(422);
    }

    public function test_refresh_forwarda_a_oauth_token(): void
    {
        Http::fake([
            '*/oauth/token' => Http::response([
                'access_token' => 'new-token',
                'refresh_token' => 'new-refresh',
                'expires_in' => 3600,
                'token_type' => 'Bearer',
            ], 200),
        ]);

        $this->postJson('/api/auth/refresh', [
            'refresh_token' => 'old-refresh',
            'client_id' => 'client-123',
            'client_secret' => 'secret-abc',
        ])->assertStatus(200)
          ->assertJsonPath('data.access_token', 'new-token');
    }

    public function test_refresh_devuelve_401_si_oauth_falla(): void
    {
        Http::fake([
            '*/oauth/token' => Http::response(['error' => 'invalid_grant'], 401),
        ]);

        $this->postJson('/api/auth/refresh', [
            'refresh_token' => 'invalid',
            'client_id' => 'client-123',
            'client_secret' => 'secret-abc',
        ])->assertStatus(401)
          ->assertJsonPath('error.code', 'AUTH_TOKEN_INVALID');
    }
}
