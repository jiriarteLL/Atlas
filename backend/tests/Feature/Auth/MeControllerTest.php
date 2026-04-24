<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Passport\Passport;
use Tests\TestCase;

class MeControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_me_devuelve_datos_del_usuario(): void
    {
        $user = $this->createUser(['email' => 'me@test.local', 'display_name' => 'Yo']);
        Passport::actingAs($user);

        $this->getJson('/api/auth/me')
            ->assertStatus(200)
            ->assertJsonPath('data.email', 'me@test.local')
            ->assertJsonPath('data.display_name', 'Yo')
            ->assertJsonPath('data.is_platform_admin', false);
    }

    public function test_me_incluye_companies_del_usuario(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany(['name' => 'Acme Co', 'slug' => 'acme-co']);
        $this->attachUserToCompany($user, $company, ['admin'], ['*']);
        Passport::actingAs($user);

        $response = $this->getJson('/api/auth/me')->assertStatus(200);
        $companies = $response->json('data.companies');
        $this->assertIsArray($companies);
        $this->assertEquals('acme-co', $companies[0]['slug']);
        $this->assertEquals(['admin'], $companies[0]['roles']);
    }

    public function test_me_sin_auth_retorna_401(): void
    {
        $this->getJson('/api/auth/me')->assertStatus(401);
    }

    public function test_me_platform_admin_flag(): void
    {
        $admin = $this->createPlatformAdmin();
        Passport::actingAs($admin);

        $this->getJson('/api/auth/me')
            ->assertStatus(200)
            ->assertJsonPath('data.is_platform_admin', true);
    }
}
