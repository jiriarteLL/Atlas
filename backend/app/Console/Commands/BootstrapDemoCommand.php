<?php

declare(strict_types=1);

namespace App\Console\Commands;

use Database\Seeders\DemoPoSeeder;
use Illuminate\Console\Command;

class BootstrapDemoCommand extends Command
{
    protected $signature = 'maestro:bootstrap-demo {--fresh : Ejecuta migrate:fresh antes de sembrar (pierde datos)}';

    protected $description = 'Bootstrappea el entorno de demo con credenciales PO (Acme Demo). Bloqueado en production.';

    public function handle(): int
    {
        if (app()->environment('production')) {
            $this->error('maestro:bootstrap-demo bloqueado en APP_ENV=production.');

            return self::FAILURE;
        }

        if ($this->option('fresh')) {
            $this->warn('--fresh: migrate:fresh borra todos los datos antes de sembrar.');
            $this->call('migrate:fresh', ['--force' => true]);
        } else {
            $this->call('migrate', ['--force' => true]);
        }

        $this->call('db:seed', [
            '--class' => DemoPoSeeder::class,
            '--force' => true,
        ]);

        return self::SUCCESS;
    }
}
