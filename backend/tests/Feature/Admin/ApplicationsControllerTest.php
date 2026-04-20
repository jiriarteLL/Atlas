<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ApplicationsControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_index_lista_aplicaciones(): void
    {
        $this->actingAsPlatformAdmin();
        $this->makeApp(['slug' => 'app-a']);
        $this->makeApp(['slug' => 'app-b']);

        $this->getJson('/api/admin/applications')
            ->assertStatus(200)
            ->assertJsonStructure(['data' => [['id', 'slug']]]);
    }

    public function test_store_crea_aplicacion(): void
    {
        $this->actingAsPlatformAdmin();

        $this->postJson('/api/admin/applications', [
            'name' => 'Mi App',
            'slug' => 'mi-app',
            'latest_version' => '1.0.0',
            'image_ref' => 'registry/mi-app:1.0.0',
        ])->assertStatus(201)->assertJsonPath('data.slug', 'mi-app');

        $this->assertDatabaseHas('applications', ['slug' => 'mi-app']);
    }

    public function test_store_valida_slug_format(): void
    {
        $this->actingAsPlatformAdmin();

        $this->postJson('/api/admin/applications', [
            'name' => 'Mi App',
            'slug' => 'Mi App',  // inválido: mayúsculas y espacios
        ])->assertStatus(422);
    }

    public function test_store_valida_slug_unique(): void
    {
        $this->actingAsPlatformAdmin();
        $this->makeApp(['slug' => 'dup-app']);

        $this->postJson('/api/admin/applications', [
            'name' => 'Otra',
            'slug' => 'dup-app',
        ])->assertStatus(422);
    }

    public function test_show_retorna_aplicacion(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp(['slug' => 'show-me']);

        $this->getJson("/api/admin/applications/{$app->id}")
            ->assertStatus(200)
            ->assertJsonPath('data.slug', 'show-me');
    }

    public function test_update_modifica_aplicacion(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp(['name' => 'Original']);

        $this->putJson("/api/admin/applications/{$app->id}", [
            'name' => 'Nuevo Nombre',
        ])->assertStatus(200)->assertJsonPath('data.name', 'Nuevo Nombre');
    }

    public function test_destroy_soft_delete(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();

        $this->deleteJson("/api/admin/applications/{$app->id}")->assertStatus(204);
        $this->assertSoftDeleted('applications', ['id' => $app->id]);
    }

    public function test_non_admin_recibe_403(): void
    {
        $user = $this->createUser(['is_platform_admin' => false]);
        \Laravel\Passport\Passport::actingAs($user);
        $this->getJson('/api/admin/applications')->assertStatus(403);
    }

    public function test_sin_auth_retorna_401(): void
    {
        $this->getJson('/api/admin/applications')->assertStatus(401);
    }
}
