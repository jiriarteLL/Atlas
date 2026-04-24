<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Models\Instance;
use App\Modules\Backups\Services\BackupService;
use Illuminate\Console\Command;

class RunBackups extends Command
{
    protected $signature = 'maestro:run-backups {--purge : Purga backups > 30 días tras ejecutar}';
    protected $description = 'Ejecuta backup cifrado de la BD del Maestro + BDs de todas las instancias activas.';

    public function handle(BackupService $service): int
    {
        $this->info('→ Backup Maestro DB...');
        try {
            $file = $service->backupMaestroDb();
            $this->info("  ✓ {$file}");
        } catch (\Throwable $e) {
            $this->error('  ✗ '.$e->getMessage());
            return self::FAILURE;
        }

        $this->info('→ Backup de instancias activas...');
        $count = 0;
        Instance::whereIn('status', ['healthy', 'degraded', 'suspended'])
            ->whereNull('destroyed_at')
            ->with(['application:id,slug', 'company:id,slug'])
            ->chunkById(20, function ($chunk) use ($service, &$count) {
                foreach ($chunk as $instance) {
                    try {
                        $file = $service->backupInstanceDb($instance);
                        if ($file) {
                            $this->info("  ✓ {$file}");
                            $count++;
                        }
                    } catch (\Throwable $e) {
                        $this->error("  ✗ instance {$instance->id}: ".$e->getMessage());
                    }
                }
            });

        $this->info("→ {$count} instancias respaldadas.");

        if ($this->option('purge')) {
            $this->info('→ Purgando backups > 30 días...');
            $removed = $service->purgeOldBackups(30);
            $this->info("  ✓ {$removed} backups purgados");
        }

        return self::SUCCESS;
    }
}
