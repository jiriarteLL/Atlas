<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Jobs;

use App\Models\Instance;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

/**
 * Scheduler: cada 30s (configurable), despacha un HealthCheckInstanceJob por instancia activa.
 */
class DispatchHealthChecksJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function handle(): void
    {
        Instance::whereIn('status', ['starting', 'healthy', 'degraded'])
            ->whereNull('destroyed_at')
            ->chunkById(50, function ($chunk) {
                foreach ($chunk as $instance) {
                    HealthCheckInstanceJob::dispatch($instance->id)->onQueue('health');
                }
            });
    }
}
