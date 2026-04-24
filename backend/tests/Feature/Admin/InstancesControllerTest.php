<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use App\Modules\Provisioning\Jobs\ProvisionInstanceJob;
use App\Modules\Provisioning\Services\ProvisioningEngine;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class InstancesControllerTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        $this->mock(ProvisioningEngine::class, function ($mock) {
            $mock->shouldReceive('stop')->andReturnNull();
            $mock->shouldReceive('destroy')->andReturnNull();
        });
    }

    public function test_index_lista_instancias(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $this->createInstance($app, $company);

        $this->getJson('/api/admin/instances')
            ->assertStatus(200)
            ->assertJsonStructure(['data', 'pagination']);
    }

    public function test_store_dispatcha_job(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $this->attachAppToCompany($app, $company);

        $this->postJson('/api/admin/instances', [
            'application_id' => $app->id,
            'company_id' => $company->id,
        ])->assertStatus(202)
          ->assertJsonPath('data.status', 'provisioning');

        Queue::assertPushed(ProvisionInstanceJob::class);
    }

    public function test_store_sin_licencia_retorna_409(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        // sin attachAppToCompany

        $this->postJson('/api/admin/instances', [
            'application_id' => $app->id,
            'company_id' => $company->id,
        ])->assertStatus(409)
          ->assertJsonPath('error.code', 'RESOURCE_CONFLICT');
    }

    public function test_store_duplicado_retorna_409(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $this->attachAppToCompany($app, $company);
        $this->createInstance($app, $company);

        $this->postJson('/api/admin/instances', [
            'application_id' => $app->id,
            'company_id' => $company->id,
        ])->assertStatus(409);
    }

    public function test_show_retorna_instancia(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->getJson("/api/admin/instances/{$instance->id}")
            ->assertStatus(200)
            ->assertJsonPath('data.id', $instance->id);
    }

    public function test_stop_detiene_instancia(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->postJson("/api/admin/instances/{$instance->id}/stop")
            ->assertStatus(200);
    }

    public function test_destroy_elimina_instancia(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->deleteJson("/api/admin/instances/{$instance->id}")
            ->assertStatus(204);
    }

    public function test_restart_dispatcha_job(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->postJson("/api/admin/instances/{$instance->id}/restart")
            ->assertStatus(200)
            ->assertJsonPath('data.status', 'restarting');

        Queue::assertPushed(ProvisionInstanceJob::class);
    }

    public function test_restore_solo_si_destroyed(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, ['status' => 'healthy']);

        $this->postJson("/api/admin/instances/{$instance->id}/restore")
            ->assertStatus(409);
    }

    public function test_health_history_retorna_data(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->getJson("/api/admin/instances/{$instance->id}/health-history")
            ->assertStatus(200)
            ->assertJsonStructure(['data']);
    }

    public function test_lifecycle_events_retorna_data(): void
    {
        $this->actingAsPlatformAdmin();
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);

        $this->getJson("/api/admin/instances/{$instance->id}/lifecycle-events")
            ->assertStatus(200)
            ->assertJsonStructure(['data']);
    }

    public function test_non_admin_403(): void
    {
        $user = $this->createUser(['is_platform_admin' => false]);
        \Laravel\Passport\Passport::actingAs($user);
        $this->getJson('/api/admin/instances')->assertStatus(403);
    }
}
