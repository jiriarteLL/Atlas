<?php

declare(strict_types=1);

namespace Tests\Unit\Jobs;

use App\Models\Instance;
use App\Models\InstanceHealthHistory;
use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Provisioning\Jobs\DispatchHealthChecksJob;
use App\Modules\Provisioning\Jobs\HealthCheckInstanceJob;
use App\Modules\Provisioning\Jobs\ProvisionInstanceJob;
use App\Modules\Provisioning\Jobs\PurgeDestroyedInstancesJob;
use App\Modules\Provisioning\Services\DockerApiClient;
use App\Modules\Provisioning\Services\ProvisioningEngine;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Http;
use Mockery;
use Tests\TestCase;

class ProvisioningJobsTest extends TestCase
{
    use RefreshDatabase;

    public function test_provision_instance_job_llama_engine(): void
    {
        $engine = Mockery::mock(ProvisioningEngine::class);
        $engine->shouldReceive('provision')->once();

        $app = $this->makeApp();
        $company = $this->createCompany();

        $job = new ProvisionInstanceJob($app->id, $company->id);
        $job->handle($engine);

        $this->assertEquals([1, 5, 30, 120, 600], $job->backoff());
    }

    public function test_dispatch_health_checks_itera_instancias_activas(): void
    {
        Bus::fake();
        $app = $this->makeApp();
        $c1 = $this->createCompany();
        $c2 = $this->createCompany();
        $c3 = $this->createCompany();
        $this->createInstance($app, $c1, ['status' => 'healthy']);
        $this->createInstance($app, $c2, ['status' => 'starting']);
        $this->createInstance($app, $c3, ['status' => 'suspended']); // no debe despacharse

        (new DispatchHealthChecksJob())->handle();

        Bus::assertDispatchedTimes(HealthCheckInstanceJob::class, 2);
    }

    public function test_health_check_instance_job_ok_marca_healthy(): void
    {
        $app = $this->makeApp(['maestro_yaml' => ['health' => ['endpoint' => '/health']]]);
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'starting',
            'container_id' => 'ctr-x',
        ]);

        Http::fake(fn () => Http::response('ok', 200));

        $docker = Mockery::mock(DockerApiClient::class);
        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        (new HealthCheckInstanceJob($instance->id))->handle($docker, $audit);

        $fresh = $instance->fresh();
        $this->assertEquals('healthy', $fresh->status);
        $this->assertDatabaseHas('instance_health_history', [
            'instance_id' => $instance->id,
            'status' => 'ok',
        ]);
    }

    public function test_health_check_instance_job_fail_marca_degraded(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'healthy',
            'container_id' => 'ctr-y',
        ]);

        Http::fake(fn () => Http::response('err', 500));

        $docker = Mockery::mock(DockerApiClient::class);
        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        (new HealthCheckInstanceJob($instance->id))->handle($docker, $audit);

        $this->assertEquals('degraded', $instance->fresh()->status);
    }

    public function test_health_check_instance_job_timeout_se_registra(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, ['status' => 'healthy']);

        Http::fake(function () {
            throw new \RuntimeException('connect timeout');
        });

        $docker = Mockery::mock(DockerApiClient::class);
        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        (new HealthCheckInstanceJob($instance->id))->handle($docker, $audit);

        $this->assertDatabaseHas('instance_health_history', [
            'instance_id' => $instance->id,
            'status' => 'timeout',
        ]);
    }

    public function test_health_check_instance_job_skip_si_destruida(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'destroyed',
            'destroyed_at' => now(),
        ]);

        Http::fake();
        $docker = Mockery::mock(DockerApiClient::class);
        $audit = Mockery::mock(AuditLogger::class);

        (new HealthCheckInstanceJob($instance->id))->handle($docker, $audit);

        Http::assertNothingSent();
    }

    public function test_purge_destroyed_instances_job_procesa_elegibles(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'destroyed',
            'destroyed_at' => now()->subDays(91),
            'purge_eligible_at' => now()->subDay(),
            'container_id' => 'ctr-old',
        ]);

        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldReceive('removeContainer')->twice();
        $docker->shouldReceive('removeNetwork')->once();
        $audit = Mockery::mock(AuditLogger::class);
        $audit->shouldReceive('log');

        (new PurgeDestroyedInstancesJob())->handle($docker, $audit);

        $fresh = $instance->fresh();
        $this->assertEquals('purged', $fresh->status);
        $this->assertNotNull($fresh->purged_at);
    }

    public function test_purge_destroyed_ignora_no_elegibles(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'status' => 'destroyed',
            'destroyed_at' => now()->subDay(),
            'purge_eligible_at' => now()->addDays(89),
        ]);

        $docker = Mockery::mock(DockerApiClient::class);
        $docker->shouldNotReceive('removeContainer');
        $audit = Mockery::mock(AuditLogger::class);

        (new PurgeDestroyedInstancesJob())->handle($docker, $audit);

        $this->assertEquals('destroyed', $instance->fresh()->status);
    }
}
