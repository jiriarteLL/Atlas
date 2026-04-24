<?php

declare(strict_types=1);

namespace Tests\Unit\Modules;

use App\Modules\Auth\Services\TokenIssuer;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TokenIssuerTest extends TestCase
{
    use RefreshDatabase;

    /**
     * TokenIssuer requiere un Personal Access Client de Passport
     * que no está seedeado en tests. Lo cubrimos en E2E.
     */
    public function test_requires_passport_personal_access_client_e2e(): void
    {
        $this->assertInstanceOf(TokenIssuer::class, app(TokenIssuer::class));
    }
}
