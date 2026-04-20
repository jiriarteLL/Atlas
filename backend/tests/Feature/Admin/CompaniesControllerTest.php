<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CompaniesControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_index_lista_empresas(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createCompany(['name' => 'Acme', 'slug' => 'acme', 'subdomain' => 'acme']);
        $this->createCompany(['name' => 'Foo', 'slug' => 'foo', 'subdomain' => 'foo']);

        $this->getJson('/api/admin/companies')
            ->assertStatus(200)
            ->assertJsonStructure(['data' => [['id', 'name', 'slug']]]);
    }

    public function test_index_filtra_por_search(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createCompany(['name' => 'Acme', 'slug' => 'acme', 'subdomain' => 'acme']);
        $this->createCompany(['name' => 'Foo', 'slug' => 'foo', 'subdomain' => 'foo']);

        $response = $this->getJson('/api/admin/companies?search=acme')->assertStatus(200);
        $this->assertCount(1, $response->json('data'));
    }

    public function test_index_filtra_por_status(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createCompany(['status' => 'active']);
        $this->createCompany(['status' => 'suspended']);

        $response = $this->getJson('/api/admin/companies?status=suspended')->assertStatus(200);
        $this->assertCount(1, $response->json('data'));
    }

    public function test_store_crea_empresa(): void
    {
        $this->actingAsPlatformAdmin();

        $this->postJson('/api/admin/companies', [
            'name' => 'Nueva',
            'slug' => 'nueva',
            'subdomain' => 'nueva',
        ])->assertStatus(201)->assertJsonPath('data.slug', 'nueva');

        $this->assertDatabaseHas('companies', ['slug' => 'nueva']);
    }

    public function test_store_valida_slug_unique(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createCompany(['slug' => 'duplicada', 'subdomain' => 'duplicada']);

        $this->postJson('/api/admin/companies', [
            'name' => 'Nueva',
            'slug' => 'duplicada',
            'subdomain' => 'otra',
        ])->assertStatus(422);
    }

    public function test_show_retorna_empresa(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany(['name' => 'Target']);

        $this->getJson("/api/admin/companies/{$company->id}")
            ->assertStatus(200)
            ->assertJsonPath('data.name', 'Target');
    }

    public function test_show_inexistente_retorna_404(): void
    {
        $this->actingAsPlatformAdmin();
        $this->getJson('/api/admin/companies/00000000-0000-0000-0000-000000000000')
            ->assertStatus(404);
    }

    public function test_update_modifica_empresa(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany(['name' => 'Original']);

        $this->putJson("/api/admin/companies/{$company->id}", [
            'name' => 'Modificada',
        ])->assertStatus(200)->assertJsonPath('data.name', 'Modificada');
    }

    public function test_destroy_soft_delete(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany();

        $this->deleteJson("/api/admin/companies/{$company->id}")->assertStatus(204);
        $this->assertSoftDeleted('companies', ['id' => $company->id]);
    }

    public function test_sin_auth_retorna_401(): void
    {
        $this->getJson('/api/admin/companies')->assertStatus(401);
    }
}
