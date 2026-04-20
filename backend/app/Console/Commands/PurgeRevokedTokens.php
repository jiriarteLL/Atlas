<?php

declare(strict_types=1);

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class PurgeRevokedTokens extends Command
{
    protected $signature = 'maestro:purge-revoked-tokens';
    protected $description = 'Elimina registros de revoked_tokens cuyo expires_at ya venció.';

    public function handle(): int
    {
        $count = DB::table('revoked_tokens')
            ->where('expires_at', '<', now())
            ->delete();

        $this->info("Eliminados {$count} revoked_tokens expirados.");
        return self::SUCCESS;
    }
}
