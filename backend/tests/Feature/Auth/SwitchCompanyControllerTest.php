<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Passport\Passport;
use Tests\TestCase;

class SwitchCompanyControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_switch_company_sin_auth_401(): void
    {
        $this->postJson('/api/auth/switch-company')->assertStatus(401);
    }

    public function test_switch_company_valida_uuid(): void
    {
        $user = $this->createUser();
        Passport::actingAs($user);
        $this->postJson('/api/auth/switch-company', ['company_id' => 'not-a-uuid'])
            ->assertStatus(422);
    }

    public function test_switch_company_no_miembro_retorna_403(): void
    {
        $user = $this->createUser();
        $otraCompany = $this->createCompany();
        Passport::actingAs($user);

        $this->postJson('/api/auth/switch-company', ['company_id' => $otraCompany->id])
            ->assertStatus(403);
    }

    // El happy path requiere un Personal Access Client de Passport (createToken)
    // que no está seedeado en tests con RefreshDatabase. Se cubre en E2E.
}
