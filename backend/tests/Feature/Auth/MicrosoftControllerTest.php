<?php

declare(strict_types=1);

namespace Tests\Feature\Auth;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MicrosoftControllerTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        // DEC-026: por defecto el feature flag está en false. Los tests del flujo OAuth lo activan explícitamente.
        config(['services.microsoft.enabled' => true]);
    }

    public function test_redirect_envia_a_microsoft_con_state(): void
    {
        config(['services.microsoft.tenant' => 'test-tenant']);
        config(['services.microsoft.client_id' => 'test-client']);
        config(['services.microsoft.redirect' => 'http://localhost/auth/microsoft/callback']);

        $response = $this->get('/api/auth/microsoft/redirect');

        $response->assertStatus(302);
        $location = $response->headers->get('Location');
        $this->assertStringContainsString('login.microsoftonline.com/test-tenant/oauth2/v2.0/authorize', $location);
        $this->assertStringContainsString('client_id=test-client', $location);
        $this->assertStringContainsString('state=', $location);
        $this->assertStringContainsString('nonce=', $location);
    }

    public function test_callback_state_invalido_redirige_a_error(): void
    {
        $response = $this->get('/api/auth/microsoft/callback?state=invalid&code=x');

        $response->assertStatus(302);
        $this->assertStringContainsString('reason=state_invalid', $response->headers->get('Location'));
    }

    public function test_callback_sin_code_redirige_a_error(): void
    {
        $response = $this->get('/api/auth/microsoft/callback');

        $response->assertStatus(302);
        $this->assertStringContainsString('reason=state_invalid', $response->headers->get('Location'));
    }

    public function test_redirect_devuelve_503_cuando_feature_flag_desactivado(): void
    {
        config(['services.microsoft.enabled' => false]);

        $response = $this->get('/api/auth/microsoft/redirect');

        $response->assertStatus(503);
        $response->assertJsonPath('error.code', 'entra_disabled');
    }

    public function test_callback_devuelve_503_cuando_feature_flag_desactivado(): void
    {
        config(['services.microsoft.enabled' => false]);

        $response = $this->get('/api/auth/microsoft/callback?state=x&code=y');

        $response->assertStatus(503);
        $response->assertJsonPath('error.code', 'entra_disabled');
    }
}
