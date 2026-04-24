<?php

declare(strict_types=1);

namespace Tests\Feature\Platform;

use Tests\TestCase;

class HealthTest extends TestCase
{
    public function test_health_endpoint_responde_sin_auth(): void
    {
        $response = $this->getJson('/api/platform/health');
        $response->assertOk()
            ->assertJsonStructure(['status', 'checks', 'version', 'timestamp']);
    }
}
