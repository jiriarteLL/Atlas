<?php

declare(strict_types=1);

namespace Tests\Unit\Jobs;

use App\Modules\Hooks\Jobs\DeliverHookJob;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class DeliverHookJobTest extends TestCase
{
    use RefreshDatabase;

    public function test_backoff_devuelve_escalado_exponencial(): void
    {
        $job = new DeliverHookJob('app', 'company', 'evt', '/hook', 'd1', []);
        $this->assertEquals([1, 5, 30, 120, 600], $job->backoff());
    }

    public function test_app_inexistente_no_despacha(): void
    {
        Http::fake();
        $job = new DeliverHookJob(
            (string) Str::uuid(), (string) Str::uuid(),
            'user.added', '/hook', (string) Str::uuid(), ['x' => 1]
        );
        $job->handle();
        Http::assertNothingSent();
    }

    public function test_sin_instancia_activa_registra_failed(): void
    {
        Http::fake();
        $app = $this->makeApp(['webhook_secret_encrypted' => encrypt('s-32-plus-chars-aaaaaaaaaaaaaaaaaaaaaaa')]);
        $company = $this->createCompany();
        $deliveryId = (string) Str::uuid();

        $job = new DeliverHookJob(
            $app->id, $company->id, 'user.added', '/hook', $deliveryId, ['x' => 1]
        );
        $job->handle();

        $this->assertDatabaseHas('hooks_deliveries', [
            'id' => $deliveryId,
            'status' => 'failed',
            'last_failure_reason' => 'no_active_instance',
        ]);
    }

    public function test_sin_webhook_secret_registra_failed(): void
    {
        Http::fake();
        $app = $this->makeApp(['webhook_secret_encrypted' => null]);
        $company = $this->createCompany();
        $this->createInstance($app, $company, ['status' => 'healthy']);
        $deliveryId = (string) Str::uuid();

        $job = new DeliverHookJob(
            $app->id, $company->id, 'user.added', '/hook', $deliveryId, ['x' => 1]
        );
        $job->handle();

        $this->assertDatabaseHas('hooks_deliveries', [
            'id' => $deliveryId,
            'status' => 'failed',
            'last_failure_reason' => 'missing_webhook_secret',
        ]);
    }

    public function test_entrega_exitosa_registra_delivered(): void
    {
        Http::fake(fn () => Http::response(['ok' => true], 200));
        $app = $this->makeApp(['webhook_secret_encrypted' => encrypt('mysecret_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')]);
        $company = $this->createCompany();
        $this->createInstance($app, $company, ['status' => 'healthy']);
        $deliveryId = (string) Str::uuid();

        $job = new DeliverHookJob(
            $app->id, $company->id, 'license.granted', '/hook', $deliveryId, ['foo' => 'bar']
        );
        $job->handle();

        $this->assertDatabaseHas('hooks_deliveries', [
            'id' => $deliveryId,
            'status' => 'delivered',
            'last_response_code' => 200,
        ]);
    }
}
