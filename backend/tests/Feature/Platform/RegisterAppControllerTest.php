<?php

declare(strict_types=1);

namespace Tests\Feature\Platform;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class RegisterAppControllerTest extends TestCase
{
    use RefreshDatabase;

    public function test_sin_secret_retorna_401(): void
    {
        $this->postJson('/api/v1/apps/register', [])
            ->assertStatus(401)
            ->assertJsonPath('error.code', 'AUTH_TOKEN_MISSING');
    }

    public function test_con_secret_y_sin_payload_retorna_422(): void
    {
        $this->withHeaders(['X-Maestro-App-Secret' => 'abc'])
            ->postJson('/api/v1/apps/register', [])
            ->assertStatus(422);
    }

    public function test_app_no_registrada_retorna_404(): void
    {
        $this->withHeaders(['X-Maestro-App-Secret' => 'abc'])
            ->postJson('/api/v1/apps/register', [
                'name' => 'nope',
                'slug' => 'no-existe',
                'version' => '1.0.0',
                'image' => 'reg/nope:1.0.0',
                'maestro_yaml' => "name: nope\n",
            ])->assertStatus(404)
              ->assertJsonPath('error.code', 'RESOURCE_NOT_FOUND');
    }

    public function test_secret_invalido_retorna_401(): void
    {
        $app = $this->makeApp([
            'slug' => 'real-app',
            'webhook_secret_encrypted' => encrypt('correct-secret'),
        ]);

        $this->withHeaders(['X-Maestro-App-Secret' => 'wrong-secret'])
            ->postJson('/api/v1/apps/register', [
                'name' => 'real-app',
                'slug' => 'real-app',
                'version' => '1.0.0',
                'image' => 'reg/real-app:1.0.0',
                'maestro_yaml' => "name: real-app\n",
            ])->assertStatus(401)
              ->assertJsonPath('error.code', 'AUTH_TOKEN_INVALID');
    }

    public function test_secret_valido_actualiza_app(): void
    {
        $secret = 'super-secret-123';
        $app = $this->makeApp([
            'slug' => 'reg-app',
            'webhook_secret_encrypted' => encrypt($secret),
        ]);

        $this->withHeaders(['X-Maestro-App-Secret' => $secret])
            ->postJson('/api/v1/apps/register', [
                'name' => 'reg-app',
                'slug' => 'reg-app',
                'version' => '2.5.1',
                'image' => 'reg/reg-app:2.5.1',
                'maestro_yaml' => "name: reg-app\nversion: 2.5.1\n",
            ])->assertStatus(200);

        $this->assertDatabaseHas('applications', [
            'id' => $app->id,
            'latest_version' => '2.5.1',
            'image_ref' => 'reg/reg-app:2.5.1',
        ]);
    }

    public function test_yaml_invalido_retorna_422(): void
    {
        $secret = 'ok-secret';
        $this->makeApp([
            'slug' => 'bad-yaml-app',
            'webhook_secret_encrypted' => encrypt($secret),
        ]);

        $this->withHeaders(['X-Maestro-App-Secret' => $secret])
            ->postJson('/api/v1/apps/register', [
                'name' => 'bad-yaml-app',
                'slug' => 'bad-yaml-app',
                'version' => '1.0.0',
                'image' => 'reg/bad-yaml-app:1.0.0',
                'maestro_yaml' => "::: invalid yaml :::\n- [unclosed",
            ])->assertStatus(422)
              ->assertJsonPath('error.code', 'CONTRACT_INVALID');
    }
}
