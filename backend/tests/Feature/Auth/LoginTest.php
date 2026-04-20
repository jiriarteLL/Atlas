<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class LoginTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Cache::flush();
    }

    public function test_login_con_credenciales_invalidas_retorna_401(): void
    {
        User::create([
            'email' => 'alice@test.local',
            'display_name' => 'Alice',
            'password_hash' => Hash::make('password_correcto_123'),
        ]);

        $this->postJson('/api/auth/login', [
            'email' => 'alice@test.local',
            'password' => 'password_incorrecto',
        ])->assertStatus(401);
    }

    public function test_login_sin_email_retorna_422(): void
    {
        $this->postJson('/api/auth/login', ['password' => 'x'])
            ->assertStatus(422);
    }

    public function test_login_registra_fallo_en_audit_log(): void
    {
        $this->postJson('/api/auth/login', [
            'email' => 'inexistente@test.local',
            'password' => 'x',
        ]);

        $this->assertDatabaseHas('audit_log', ['action' => 'auth.login.fail']);
    }

    /**
     * El happy path requiere PassportClientsSeeder + env vars configuradas.
     * Se valida E2E en dev. Unit test del controller en tests/Unit.
     */
    public function test_login_happy_path_requiere_e2e_entorno(): void
    {
        $this->markTestSkipped('Login happy path requiere Password Grant client + env vars; testeado E2E.');
    }
}
