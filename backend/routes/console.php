<?php

use App\Modules\Provisioning\Jobs\DispatchHealthChecksJob;
use App\Modules\Provisioning\Jobs\PurgeDestroyedInstancesJob;
use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', fn () => $this->comment(Inspiring::quote()))
    ->purpose('Cita inspiradora');

// Health checks cada 30s: despacha jobs para cada instancia activa
Schedule::job(new DispatchHealthChecksJob())
    ->everyThirtySeconds()
    ->withoutOverlapping();

// Purga diaria de instancias cuyo periodo de retención (90d) venció (DEC-019)
Schedule::job(new PurgeDestroyedInstancesJob())
    ->dailyAt('03:00')
    ->withoutOverlapping();

// Purga de revoked_tokens expirados (job simple)
Schedule::command('maestro:purge-revoked-tokens')->daily();

// Backup diario cifrado de BD Maestro + instancias (RF-110/111/112, RNF-030, DEC-019)
Schedule::command('maestro:run-backups --purge')
    ->dailyAt(env('BACKUP_DAILY_AT', '02:00'))
    ->withoutOverlapping();
