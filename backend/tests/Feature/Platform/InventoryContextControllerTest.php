<?php

declare(strict_types=1);

namespace Tests\Feature\Platform;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class InventoryContextControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_sin_headers_auth_retorna_401(): void
    {
        $this->getJson('/api/v1/inventory/context')
            ->assertStatus(401)
            ->assertJsonPath('error.code', 'AUTH_TOKEN_MISSING');
    }

    public function test_con_headers_retorna_contexto(): void
    {
        $user = $this->createUser(['email' => 'sdk@test.local', 'display_name' => 'SDK User']);
        $company = $this->createCompany(['name' => 'SdkCo', 'slug' => 'sdkco']);

        $response = $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
        ])->getJson('/api/v1/inventory/context')->assertStatus(200);

        $this->assertEquals($user->id, $response->json('data.user.id'));
        $this->assertEquals($company->id, $response->json('data.company.id'));
        $this->assertNull($response->json('data.application'));
    }

    public function test_con_app_slug_incluye_aplicacion(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $app = $this->makeApp(['slug' => 'my-app', 'latest_version' => '2.1.0']);

        $this->withHeaders([
            'X-Auth-User-Id' => $user->id,
            'X-Auth-Company-Id' => $company->id,
        ])->getJson('/api/v1/inventory/context?app=my-app')
            ->assertStatus(200)
            ->assertJsonPath('data.application.slug', 'my-app')
            ->assertJsonPath('data.application.version', '2.1.0');
    }
}
