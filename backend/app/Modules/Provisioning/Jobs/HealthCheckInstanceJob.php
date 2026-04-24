<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Jobs;

use App\Models\Instance;
use App\Models\InstanceHealthHistory;
use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Provisioning\Services\DockerApiClient;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;

/**
 * Ejecuta un health check contra una instancia y actúa según resultado.
 * No-negociable 8: 3 fallos consecutivos → restart; 5 → alerta admin; 10 → suspender.
 */
class HealthCheckInstanceJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public readonly string $instanceId) {}

    public function handle(DockerApiClient $docker, AuditLogger $audit): void
    {
        $instance = Instance::find($this->instanceId);
        if (! $instance || in_array($instance->status, ['destroyed', 'purged', 'suspended'], true)) {
            return;
        }

        $start = microtime(true);
        $endpoint = $this->extractHealthEndpoint($instance);
        $url = "http://{$instance->containerName()}{$endpoint}";

        try {
            $response = Http::timeout(5)->get($url);
            $responseMs = (int) ((microtime(true) - $start) * 1000);
            $ok = $response->successful();

            InstanceHealthHistory::create([
                'instance_id' => $instance->id,
                'at' => now(),
                'status' => $ok ? 'ok' : 'fail',
                'response_ms' => $responseMs,
                'http_code' => $response->status(),
                'failure_reason' => $ok ? null : "status={$response->status()}",
            ]);

            if ($ok) {
                $instance->last_healthy_at = now();
                $instance->save();

                // Transición starting → healthy
                if ($instance->status === 'starting' && $instance->canTransitionTo('healthy')) {
                    $instance->transitionTo('healthy', ['source' => 'health_check']);
                }
                // Recuperación degraded → healthy
                if ($instance->status === 'degraded' && $instance->canTransitionTo('healthy')) {
                    $instance->transitionTo('healthy', ['source' => 'health_check_recovery']);
                }
            } else {
                $this->handleFailure($instance, $docker, $audit, "http_{$response->status()}");
            }
        } catch (\Throwable $e) {
            InstanceHealthHistory::create([
                'instance_id' => $instance->id,
                'at' => now(),
                'status' => 'timeout',
                'failure_reason' => $e->getMessage(),
            ]);
            $this->handleFailure($instance, $docker, $audit, 'timeout');
        }
    }

    private function handleFailure(Instance $instance, DockerApiClient $docker, AuditLogger $audit, string $reason): void
    {
        $recentFailures = $instance->healthHistory()
            ->where('at', '>=', now()->subMinutes(5))
            ->where('status', '!=', 'ok')
            ->count();

        if ($instance->status === 'healthy' && $instance->canTransitionTo('degraded')) {
            $instance->transitionTo('degraded', ['reason' => $reason, 'consecutive_failures' => $recentFailures]);
        }

        if ($recentFailures >= 3 && $instance->container_id) {
            $audit->log('instance.auto_restart', resourceType: 'instance', resourceId: $instance->id,
                dataAfter: ['consecutive_failures' => $recentFailures]);
            try {
                $docker->stopContainer($instance->container_id);
                $docker->startContainer($instance->container_id);
            } catch (\Throwable $e) {
                $audit->log('instance.auto_restart.failed', resourceType: 'instance', resourceId: $instance->id,
                    dataAfter: ['error' => $e->getMessage()]);
            }
        }

        if ($recentFailures >= 10 && $instance->canTransitionTo('suspended')) {
            $instance->transitionTo('suspended', ['reason' => 'repeated_health_failures']);
            $audit->log('instance.auto_suspended', resourceType: 'instance', resourceId: $instance->id);
        }
    }

    private function extractHealthEndpoint(Instance $instance): string
    {
        $yaml = $instance->application?->maestro_yaml;
        $endpoint = $yaml['health']['endpoint'] ?? '/health';
        return str_starts_with($endpoint, '/') ? $endpoint : "/{$endpoint}";
    }
}
