<?php

declare(strict_types=1);

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * Crea el Password Grant client de Passport v13 si no existe.
 *
 * En v13 los oauth_clients usan columna `grant_types` TEXT con lista CSV.
 * El secret se guarda hasheado; el plaintext se muestra una sola vez en consola
 * para copiar al .env del Maestro.
 */
class PassportClientsSeeder extends Seeder
{
    public function run(): void
    {
        $existing = DB::table('oauth_clients')
            ->where('name', 'Maestro Password Grant')
            ->first();

        if ($existing) {
            $this->command->info('Password Grant client ya existe; no se recrea.');
            $this->command->warn("PASSPORT_PASSWORD_CLIENT_ID={$existing->id}");
            $this->command->warn('(secret ya generado; si lo perdiste, borrá el client y re-seed)');
            return;
        }

        $clientId = (string) Str::uuid();
        $plainSecret = Str::random(40);

        DB::table('oauth_clients')->insert([
            'id' => $clientId,
            'name' => 'Maestro Password Grant',
            'secret' => Hash::make($plainSecret),   // Passport v13 hashea secrets
            'provider' => 'users',
            'redirect_uris' => json_encode([]),
            'grant_types' => json_encode(['password', 'refresh_token']),
            'revoked' => false,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        $this->command->info('=== Maestro Password Grant client creado ===');
        $this->command->warn('Copiar a .env (el secret NO se puede recuperar después):');
        $this->command->warn("PASSPORT_PASSWORD_CLIENT_ID={$clientId}");
        $this->command->warn("PASSPORT_PASSWORD_CLIENT_SECRET={$plainSecret}");
    }
}
