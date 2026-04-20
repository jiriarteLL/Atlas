<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class LogoutControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_logout_sin_auth_retorna_401(): void
    {
        $this->postJson('/api/auth/logout')->assertStatus(401);
    }

    // Flujo happy-path requiere un JWT real emitido por Passport con jti
    // no-nulo. Se cubre en tests E2E via scripts de smoke test (fuera del
    // suite unitario por limitación de Passport::actingAs).
}
