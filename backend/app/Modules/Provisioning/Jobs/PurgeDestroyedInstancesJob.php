<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Jobs;

use App\Models\Instance;
use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Provisioning\Services\DockerApiClient;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

/**
 * Job diario que purga instancias destroyed cuya ventana de retención (90 días) venció (DEC-019).
 */
class PurgeDestroyedInstancesJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function handle(DockerApiClient $docker, AuditLogger $audit): void
    {
        Instance::where('status', 'destroyed')
            ->whereNotNull('purge_eligible_at')
            ->where('purge_eligible_at', '<=', now())
            ->whereNull('purged_at')
            ->chunkById(20, function ($chunk) use ($docker, $audit) {
                foreach ($chunk as $instance) {
                    $this->purge($instance, $docker, $audit);
                }
            });
    }

    private function purge(Instance $instance, DockerApiClient $docker, AuditLogger $audit): void
    {
        try {
            if ($instance->container_id) {
                $docker->removeContainer($instance->container_id);
            }
            $docker->removeContainer($instance->dbContainerName());
            $docker->removeNetwork($instance->networkName());
        } catch (\Throwable) {
            // Best-effort
        }

        $instance->purged_at = now();
        if ($instance->canTransitionTo('purged')) {
            $instance->transitionTo('purged', ['reason' => 'retention_expired']);
        }

        $audit->log('instance.purge', resourceType: 'instance', resourceId: $instance->id);
    }
}
