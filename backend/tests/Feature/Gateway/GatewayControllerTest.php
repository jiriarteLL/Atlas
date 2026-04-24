<?php

declare(strict_types=1);

namespace Tests\Feature\Gateway;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class GatewayControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_sin_auth_headers_retorna_401(): void
    {
        $this->postJson('/api/v1/gateway/target-app/ping')
            ->assertStatus(401)
            ->assertJsonPath('error.code', 'AUTH_TOKEN_MISSING');
    }

    public function test_sin_permiso_retorna_403(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
            'X-Auth-Permissions' => 'read:users',
        ])->postJson('/api/v1/gateway/target-app/ping')
            ->assertStatus(403)
            ->assertJsonPath('error.code', 'PERMISSION_DENIED');
    }

    public function test_target_inexistente_retorna_404(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
            'X-Auth-Permissions' => '*',
        ])->postJson('/api/v1/gateway/no-existe/ping')
            ->assertStatus(404)
            ->assertJsonPath('error.code', 'RESOURCE_NOT_FOUND');
    }

    public function test_target_sin_licencia_retorna_409(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $target = $this->makeApp(['slug' => 'target-x']);
        // sin attachAppToCompany

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
            'X-Auth-Permissions' => '*',
        ])->postJson('/api/v1/gateway/target-x/ping')
            ->assertStatus(409)
            ->assertJsonPath('error.code', 'RESOURCE_CONFLICT');
    }

    public function test_sin_instancia_healthy_retorna_503(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $target = $this->makeApp(['slug' => 'target-y']);
        $this->attachAppToCompany($target, $company);

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
            'X-Auth-Permissions' => 'gateway:target-y',
        ])->postJson('/api/v1/gateway/target-y/ping')
            ->assertStatus(503);
    }

    public function test_forward_exitoso(): void
    {
        Http::fake([
            '*' => Http::response('{"ok":true}', 200, ['Content-Type' => 'application/json']),
        ]);

        $user = $this->createUser();
        $company = $this->createCompany(['subdomain' => 'acme']);
        $target = $this->makeApp(['slug' => 'target-z']);
        $this->attachAppToCompany($target, $company);
        $this->createInstance($target, $company, ['status' => 'healthy']);

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
            'X-Auth-Permissions' => '*',
        ])->postJson('/api/v1/gateway/target-z/api/ping', ['hello' => 'world'])
            ->assertStatus(200);
    }
}
