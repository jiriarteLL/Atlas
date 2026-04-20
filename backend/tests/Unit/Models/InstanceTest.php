<?php

declare(strict_types=1);

namespace Tests\Unit\Models;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class InstanceTest extends TestCase
{
    use RefreshDatabase;

    public function test_can_transition_valida_transiciones(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, ['status' => 'healthy']);

        $this->assertTrue($instance->canTransitionTo('degraded'));
        $this->assertTrue($instance->canTransitionTo('destroyed'));
        $this->assertFalse($instance->canTransitionTo('provisioning'));
    }

    public function test_transition_to_cambia_estado_y_registra_evento(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, ['status' => 'healthy']);

        $instance->transitionTo('degraded', ['reason' => 'test']);
        $this->assertEquals('degraded', $instance->fresh()->status);
        $this->assertCount(1, $instance->lifecycleEvents()->get());
    }

    public function test_transition_to_invalida_lanza_excepcion(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, ['status' => 'purged']);

        $this->expectException(\DomainException::class);
        $instance->transitionTo('healthy');
    }

    public function test_helpers_retornan_nombres_deterministicos(): void
    {
        $app = $this->makeApp(['slug' => 'myapp']);
        $company = $this->createCompany(['slug' => 'acme', 'subdomain' => 'acme']);
        $instance = $this->createInstance($app, $company);

        $fresh = $instance->fresh(['application', 'company']);
        $this->assertEquals('myapp-acme', $fresh->subdomain());
        $this->assertEquals('app-myapp-acme', $fresh->containerName());
        $this->assertEquals('db-myapp-acme', $fresh->dbContainerName());
        $this->assertEquals('app-myapp-acme-net', $fresh->networkName());
    }

    public function test_is_active_solo_para_estados_activos(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();

        $healthy = $this->createInstance($app, $company, ['status' => 'healthy']);
        $this->assertTrue($healthy->isActive());

        // Nueva app/company para evitar unique constraint
        $app2 = $this->makeApp();
        $company2 = $this->createCompany();
        $destroyed = $this->createInstance($app2, $company2, ['status' => 'destroyed']);
        $this->assertFalse($destroyed->isActive());
    }
}
