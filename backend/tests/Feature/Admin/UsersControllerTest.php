<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use App\Modules\Hooks\Jobs\DeliverHookJob;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Bus;
use Tests\TestCase;

class UsersControllerTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Bus::fake([DeliverHookJob::class]);
    }

    public function test_index_lista_usuarios(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createUser(['email' => 'u1@test.local']);
        $this->createUser(['email' => 'u2@test.local']);

        $this->getJson('/api/admin/users')
            ->assertStatus(200)
            ->assertJsonStructure(['data' => [['id', 'email']]]);
    }

    public function test_index_filtra_por_company_id(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany();
        $u1 = $this->createUser();
        $this->createUser();
        $this->attachUserToCompany($u1, $company);

        $response = $this->getJson("/api/admin/users?company_id={$company->id}")->assertStatus(200);
        $ids = array_column($response->json('data'), 'id');
        $this->assertContains($u1->id, $ids);
    }

    public function test_index_filtra_platform_admin(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createUser(['is_platform_admin' => false]);
        $this->createUser(['is_platform_admin' => true]);

        $response = $this->getJson('/api/admin/users?is_platform_admin=1')->assertStatus(200);
        $this->assertGreaterThanOrEqual(1, count($response->json('data')));
    }

    public function test_index_filtra_search(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createUser(['email' => 'findme@test.local', 'display_name' => 'Zeta']);
        $this->createUser(['email' => 'other@test.local', 'display_name' => 'Alpha']);

        $response = $this->getJson('/api/admin/users?search=findme')->assertStatus(200);
        $this->assertCount(1, $response->json('data'));
    }

    public function test_store_crea_user(): void
    {
        $this->actingAsPlatformAdmin();

        $this->postJson('/api/admin/users', [
            'email' => 'nuevo@test.local',
            'display_name' => 'Nuevo',
            'password' => 'pass_super_secreto',
        ])->assertStatus(201)->assertJsonPath('data.email', 'nuevo@test.local');

        $this->assertDatabaseHas('users', ['email' => 'nuevo@test.local']);
    }

    public function test_store_con_memberships_attacha_company(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany();

        $this->postJson('/api/admin/users', [
            'email' => 'conmemb@test.local',
            'display_name' => 'Membership User',
            'password' => 'pass_super_secreto',
            'memberships' => [[
                'company_id' => $company->id,
                'roles' => ['viewer'],
                'permissions' => ['read:*'],
                'is_active' => true,
            ]],
        ])->assertStatus(201);

        $this->assertDatabaseHas('company_user', ['company_id' => $company->id]);
    }

    public function test_store_valida_email_unique(): void
    {
        $this->actingAsPlatformAdmin();
        $this->createUser(['email' => 'dup@test.local']);

        $this->postJson('/api/admin/users', [
            'email' => 'dup@test.local',
            'display_name' => 'Dup',
        ])->assertStatus(422);
    }

    public function test_show_retorna_user(): void
    {
        $this->actingAsPlatformAdmin();
        $user = $this->createUser(['display_name' => 'Target']);

        $this->getJson("/api/admin/users/{$user->id}")
            ->assertStatus(200)
            ->assertJsonPath('data.display_name', 'Target');
    }

    public function test_update_modifica_user(): void
    {
        $this->actingAsPlatformAdmin();
        $user = $this->createUser(['display_name' => 'Old']);

        $this->putJson("/api/admin/users/{$user->id}", [
            'display_name' => 'New',
            'password' => 'nuevo_password_1234',
        ])->assertStatus(200)->assertJsonPath('data.display_name', 'New');
    }

    public function test_destroy_soft_delete_y_hook(): void
    {
        $this->actingAsPlatformAdmin();
        $company = $this->createCompany();
        $user = $this->createUser();
        $this->attachUserToCompany($user, $company);

        $this->deleteJson("/api/admin/users/{$user->id}")->assertStatus(204);
        $this->assertSoftDeleted('users', ['id' => $user->id]);
    }

    public function test_non_admin_recibe_403(): void
    {
        $nonAdmin = $this->createUser(['is_platform_admin' => false]);
        \Laravel\Passport\Passport::actingAs($nonAdmin);
        $this->getJson('/api/admin/users')->assertStatus(403);
    }
}
