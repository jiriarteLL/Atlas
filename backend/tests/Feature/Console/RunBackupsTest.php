<?php

declare(strict_types=1);

namespace Tests\Feature\Console;

use App\Modules\Backups\Services\BackupService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery;
use Tests\TestCase;

class RunBackupsTest extends TestCase
{
    use RefreshDatabase;

    public function test_run_backups_ejecuta_maestro_db(): void
    {
        $svc = Mockery::mock(BackupService::class);
        $svc->shouldReceive('backupMaestroDb')->once()->andReturn('maestro-backup.sql.gz.enc');
        $this->app->instance(BackupService::class, $svc);

        $this->artisan('maestro:run-backups')->assertSuccessful();
    }

    public function test_run_backups_con_flag_purge_llama_purgar(): void
    {
        $svc = Mockery::mock(BackupService::class);
        $svc->shouldReceive('backupMaestroDb')->once()->andReturn('file.enc');
        $svc->shouldReceive('purgeOldBackups')->once()->with(30)->andReturn(5);
        $this->app->instance(BackupService::class, $svc);

        $this->artisan('maestro:run-backups', ['--purge' => true])->assertSuccessful();
    }

    public function test_run_backups_maestro_falla_retorna_failure(): void
    {
        $svc = Mockery::mock(BackupService::class);
        $svc->shouldReceive('backupMaestroDb')->once()
            ->andThrow(new \RuntimeException('pg_dump failed'));
        $this->app->instance(BackupService::class, $svc);

        $this->artisan('maestro:run-backups')->assertFailed();
    }

    public function test_run_backups_itera_instancias_activas(): void
    {
        $app = $this->makeApp();
        $c1 = $this->createCompany();
        $c2 = $this->createCompany();
        $this->createInstance($app, $c1, [
            'status' => 'healthy',
            'db_host' => 'db1',
            'db_name' => 'mydb1',
            'db_user' => 'u1',
            'db_password_encrypted' => encrypt('pw'),
        ]);
        $this->createInstance($app, $c2, ['status' => 'destroyed', 'destroyed_at' => now()]);

        $svc = Mockery::mock(BackupService::class);
        $svc->shouldReceive('backupMaestroDb')->once()->andReturn('maestro.enc');
        $svc->shouldReceive('backupInstanceDb')->once()->andReturn('instance.enc');
        $this->app->instance(BackupService::class, $svc);

        $this->artisan('maestro:run-backups')->assertSuccessful();
    }
}
