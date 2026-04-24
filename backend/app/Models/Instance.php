<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

/**
 * Instancia de una aplicación (combinación única empresa × aplicación).
 *
 * Estados válidos y transiciones:
 *   provisioning → starting → healthy ⇆ degraded
 *                    ↓            ↓       ↓
 *                  failed       suspended → destroyed → purged
 */
class Instance extends Model
{
    use HasFactory, HasUuids;

    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'application_id', 'company_id', 'status',
        'container_id', 'network_name',
        'db_host', 'db_name', 'db_user', 'db_password_encrypted',
        'image_ref', 'resources_memory', 'resources_cpu',
        'env_vars_encrypted',
        'provisioned_at', 'last_healthy_at',
        'destroyed_at', 'purge_eligible_at', 'purged_at',
    ];

    protected $hidden = ['db_password_encrypted', 'env_vars_encrypted'];

    protected function casts(): array
    {
        return [
            'provisioned_at' => 'datetime',
            'last_healthy_at' => 'datetime',
            'destroyed_at' => 'datetime',
            'purge_eligible_at' => 'datetime',
            'purged_at' => 'datetime',
        ];
    }

    // --- Transiciones válidas ---
    private const TRANSITIONS = [
        'provisioning' => ['starting', 'failed'],
        'starting' => ['healthy', 'failed'],
        'healthy' => ['degraded', 'suspended', 'destroyed'],
        'degraded' => ['healthy', 'suspended', 'destroyed'],
        'suspended' => ['starting', 'destroyed'],
        'destroyed' => ['purged'],
        'failed' => ['provisioning', 'destroyed'],
        'purged' => [],
    ];

    public function canTransitionTo(string $newStatus): bool
    {
        return in_array($newStatus, self::TRANSITIONS[$this->status] ?? [], true);
    }

    public function transitionTo(string $newStatus, array $metadata = []): void
    {
        if (! $this->canTransitionTo($newStatus)) {
            throw new \DomainException(
                "Transición inválida: {$this->status} → {$newStatus}"
            );
        }

        $previous = $this->status;
        $this->status = $newStatus;
        $this->save();

        $this->lifecycleEvents()->create([
            'at' => now(),
            'event_type' => "status_change",
            'previous_status' => $previous,
            'new_status' => $newStatus,
            'metadata' => $metadata,
        ]);
    }

    // --- Relaciones ---

    public function application(): BelongsTo
    {
        return $this->belongsTo(Application::class);
    }

    public function company(): BelongsTo
    {
        return $this->belongsTo(Company::class);
    }

    public function healthHistory(): HasMany
    {
        return $this->hasMany(InstanceHealthHistory::class);
    }

    public function lifecycleEvents(): HasMany
    {
        return $this->hasMany(InstanceLifecycleEvent::class);
    }

    // --- Helpers ---

    public function subdomain(): string
    {
        $appSlug = $this->application?->slug ?? 'unknown';
        $companySlug = $this->company?->subdomain ?? $this->company?->slug ?? 'unknown';
        return "{$appSlug}-{$companySlug}";
    }

    public function containerName(): string
    {
        return "app-{$this->application->slug}-{$this->company->slug}";
    }

    public function dbContainerName(): string
    {
        return "db-{$this->application->slug}-{$this->company->slug}";
    }

    public function networkName(): string
    {
        return "app-{$this->application->slug}-{$this->company->slug}-net";
    }

    public function isActive(): bool
    {
        return in_array($this->status, ['healthy', 'degraded', 'starting'], true);
    }
}
