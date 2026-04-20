<?php

declare(strict_types=1);

namespace Tests\Unit\Modules;

use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Provisioning\Services\DockerApiClient;
use App\Modules\Provisioning\Services\ProvisioningEngine;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery;
use Tests\TestCase;

class ProvisioningEngineTest extends TestCase
{
    use RefreshDatabase;

    public function test_stop_suspende_instancia(): void
    {
        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldReceive('stopContainer')->twice();

        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        $engine = new ProvisioningEngine($docker, $audit);

        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'healthy',
            'container_id' => 'abc123',
        ]);

        $engine->stop($instance->fresh(['application', 'company']));

        $this->assertEquals('suspended', $instance->fresh()->status);
    }

    public function test_destroy_marca_destroyed_y_purge_eligible(): void
    {
        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldReceive('stopContainer')->twice();
        $docker->shouldReceive('removeContainer')->twice();
        $docker->shouldReceive('removeNetwork')->once();

        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        $engine = new ProvisioningEngine($docker, $audit);

        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'healthy',
            'container_id' => 'ctr-1',
        ]);

        $engine->destroy($instance->fresh(['application', 'company']));

        $fresh = $instance->fresh();
        $this->assertEquals('destroyed', $fresh->status);
        $this->assertNotNull($fresh->destroyed_at);
        $this->assertNotNull($fresh->purge_eligible_at);
    }

    public function test_provision_idempotente_retorna_instancia_existente(): void
    {
        $docker = Mockery::mock(DockerApiClient::class);
        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        $engine = new ProvisioningEngine($docker, $audit);

        $app = $this->makeApp();
        $company = $this->createCompany();
        $existing = $this->createInstance($app, $company, ['status' => 'healthy']);

        $result = $engine->provision($app->fresh(), $company->fresh());

        $this->assertEquals($existing->id, $result->id);
    }

    public function test_provision_crea_red_db_y_app_container(): void
    {
        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldReceive('createNetwork')->once();
        $docker->shouldReceive('createContainer')->twice()
            ->andReturn(['Id' => 'ctr-db-id'], ['Id' => 'ctr-app-id']);
        $docker->shouldReceive('startContainer')->twice();

        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        $engine = new ProvisioningEngine($docker, $audit);

        $app = $this->makeApp(['maestro_yaml' => [
            'resources' => ['memory' => '1g', 'cpu' => '1.0'],
            'requires' => ['ports' => ['app' => 8080]],
        ]]);
        $company = $this->createCompany();

        $result = $engine->provision($app->fresh(), $company->fresh());

        $this->assertEquals('starting', $result->fresh()->status);
        $this->assertEquals('ctr-app-id', $result->fresh()->container_id);
        $this->assertNotNull($result->fresh()->db_password_encrypted);
    }

    public function test_provision_rollback_al_fallar(): void
    {
        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldReceive('createNetwork')->once();
        $docker->shouldReceive('createContainer')->once()
            ->andThrow(new \RuntimeException('docker error'));
        $docker->shouldReceive('removeContainer')->atLeast()->once();
        $docker->shouldReceive('removeNetwork')->once();

        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        $engine = new ProvisioningEngine($docker, $audit);

        $app = $this->makeApp();
        $company = $this->createCompany();

        $this->expectException(\RuntimeException::class);
        $engine->provision($app->fresh(), $company->fresh());
    }
}
