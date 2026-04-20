<?php

declare(strict_types=1);

namespace Tests\Feature\Console;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

class CommandsTest extends TestCase
{
    use RefreshDatabase;

    public function test_purge_revoked_tokens_elimina_expirados(): void
    {
        $u1 = $this->createUser();
        $u2 = $this->createUser();
        DB::table('revoked_tokens')->insert([
            ['jti' => 'expired', 'user_id' => $u1->id,
             'revoked_at' => now()->subDays(2), 'expires_at' => now()->subDay()],
            ['jti' => 'valid', 'user_id' => $u2->id,
             'revoked_at' => now(), 'expires_at' => now()->addHour()],
        ]);

        $this->artisan('maestro:purge-revoked-tokens')->assertSuccessful();

        $this->assertDatabaseMissing('revoked_tokens', ['jti' => 'expired']);
        $this->assertDatabaseHas('revoked_tokens', ['jti' => 'valid']);
    }

}
