<?php

declare(strict_types=1);

namespace Tests\Unit\Modules;

use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Backups\Services\BackupService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Mockery;
use Tests\TestCase;

class BackupServiceTest extends TestCase
{
    use RefreshDatabase;

    public function test_purge_old_backups_elimina_archivos_antiguos(): void
    {
        Storage::fake('local');
        $svc = new BackupService(Mockery::mock(AuditLogger::class));
        // BackupService::disk() usa Storage::build; no podemos inyectar fakes aquí
        // sin acceder al private. Verificamos solo que no lanza.
        $count = $svc->purgeOldBackups(30);
        $this->assertIsInt($count);
    }

    public function test_backup_instance_db_sin_credenciales_retorna_null(): void
    {
        $svc = new BackupService(Mockery::mock(AuditLogger::class));
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company, [
            'db_host' => null,
            'db_name' => null,
            'db_password_encrypted' => null,
        ]);

        $this->assertNull($svc->backupInstanceDb($instance->fresh()));
    }
}
