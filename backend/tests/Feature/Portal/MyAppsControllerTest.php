<?php

declare(strict_types=1);

namespace Tests\Feature\Portal;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Passport\Passport;
use Tests\TestCase;

class MyAppsControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_sin_auth_retorna_401(): void
    {
        $this->getJson('/api/portal/my-apps')->assertStatus(401);
    }

    public function test_usuario_sin_company_activa_retorna_lista_vacia(): void
    {
        $user = $this->createUser();
        Passport::actingAs($user);

        $this->getJson('/api/portal/my-apps')
            ->assertStatus(200)
            ->assertJson(['data' => []]);
    }

    public function test_retorna_apps_licenciadas_a_la_empresa_activa(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany(['subdomain' => 'acme']);
        $app = $this->makeApp(['slug' => 'analytics']);

        $this->attachUserToCompany($user, $company);
        $this->attachAppToCompany($app, $company);

        $user->update(['active_company_id' => $company->id]);
        $app->users()->attach($user->id, [
            'company_id' => $company->id,
            'roles' => json_encode(['user']),
            'permissions' => json_encode(['*']),
        ]);

        Passport::actingAs($user->fresh());

        $response = $this->getJson('/api/portal/my-apps')->assertStatus(200);
        $data = $response->json('data');

        $this->assertCount(1, $data);
        $this->assertEquals('analytics', $data[0]['slug']);
        $this->assertEquals('not_provisioned', $data[0]['status']);
        $this->assertTrue($data[0]['license_active']);
    }

    public function test_apps_no_licenciadas_no_aparecen(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $otroCompany = $this->createCompany();
        $app = $this->makeApp(['slug' => 'no-licenciada']);

        $this->attachUserToCompany($user, $company);
        $this->attachAppToCompany($app, $otroCompany);
        $user->update(['active_company_id' => $company->id]);

        Passport::actingAs($user->fresh());

        $this->getJson('/api/portal/my-apps')
            ->assertStatus(200)
            ->assertJson(['data' => []]);
    }
}
