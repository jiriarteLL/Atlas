<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ForwardAuthControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_validate_sin_bearer_retorna_401(): void
    {
        $this->get('/api/auth/validate')->assertStatus(401);
    }

    public function test_validate_con_bearer_invalido_retorna_401(): void
    {
        $this->withHeaders(['Authorization' => 'Bearer token-invalido'])
            ->get('/api/auth/validate')
            ->assertStatus(401);
    }

    public function test_validate_header_sin_prefijo_bearer_retorna_401(): void
    {
        $this->withHeaders(['Authorization' => 'some-opaque-value'])
            ->get('/api/auth/validate')
            ->assertStatus(401);
    }
}
