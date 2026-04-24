<?php

declare(strict_types=1);

namespace App\Modules\Hooks\Jobs;

use App\Models\Application;
use App\Models\Instance;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;

/**
 * Entrega un hook saliente firmado HMAC-SHA256 a una app huésped.
 * Retry backoff 1s/5s/30s/2m/10m. Tras agotar → marca failed.
 */
class DeliverHookJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 5;

    public function __construct(
        public readonly string $applicationId,
        public readonly string $companyId,
        public readonly string $eventType,
        public readonly string $endpoint,
        public readonly string $deliveryId,
        public readonly array $payload,
    ) {}

    public function backoff(): array
    {
        return [1, 5, 30, 120, 600];
    }

    public function handle(): void
    {
        $app = Application::find($this->applicationId);
        if (! $app) return;

        // Buscar instancia healthy para la app en la company
        $instance = Instance::where('application_id', $this->applicationId)
            ->where('company_id', $this->companyId)
            ->whereIn('status', ['healthy', 'degraded'])
            ->first();
        if (! $instance) {
            $this->recordDelivery('failed', 0, 'no_active_instance', null);
            return;
        }

        $webhookSecret = $app->webhook_secret_encrypted
            ? Crypt::decryptString($app->webhook_secret_encrypted)
            : null;
        if (! $webhookSecret) {
            $this->recordDelivery('failed', 0, 'missing_webhook_secret', null);
            return;
        }

        $baseDomain = config('app.base_domain', 'maestro.local');
        $url = "https://{$app->slug}-{$instance->company->subdomain}.{$baseDomain}".
               (str_starts_with($this->endpoint, '/') ? $this->endpoint : '/'.$this->endpoint);

        $body = json_encode($this->payload, JSON_THROW_ON_ERROR);
        $hmac = hash_hmac('sha256', $body, $webhookSecret);
        $timestamp = (string) now()->timestamp;

        try {
            $response = Http::withHeaders([
                'Content-Type' => 'application/json',
                'X-Maestro-Webhook-Secret' => $hmac,
                'X-Maestro-Event' => $this->eventType,
                'X-Maestro-Delivery-Id' => $this->deliveryId,
                'X-Maestro-Delivery-Timestamp' => $timestamp,
            ])->timeout(10)->withBody($body, 'application/json')->post($url);

            $ok = $response->successful();
            $this->recordDelivery(
                status: $ok ? 'delivered' : 'failed',
                responseCode: $response->status(),
                reason: $ok ? null : "http_{$response->status()}",
                hmac: $hmac,
            );

            if (! $ok) {
                $this->fail(new \RuntimeException("Hook delivery failed: HTTP {$response->status()}"));
            }
        } catch (\Throwable $e) {
            $this->recordDelivery('failed', 0, $e->getMessage(), $hmac);
            throw $e; // re-throw para que el queue retry
        }
    }

    private function recordDelivery(string $status, int $responseCode, ?string $reason, ?string $hmac): void
    {
        DB::table('hooks_deliveries')->updateOrInsert(
            ['id' => $this->deliveryId],
            [
                'application_id' => $this->applicationId,
                'company_id' => $this->companyId,
                'event_type' => $this->eventType,
                'payload' => json_encode($this->payload),
                'payload_hmac' => $hmac,
                'status' => $status,
                'attempts' => $this->attempts(),
                'last_attempt_at' => now(),
                'last_response_code' => $responseCode ?: null,
                'last_failure_reason' => $reason,
                'created_at' => now(),
            ],
        );
    }
}
