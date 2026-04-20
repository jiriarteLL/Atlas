<?php

declare(strict_types=1);

namespace App\Modules\AuditLog\Observers;

use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Database\Eloquent\Model;

/**
 * Observer global que registra create/update/delete sobre modelos críticos
 * (users, companies, applications) en audit_log.
 */
class AuditableObserver
{
    public function __construct(private readonly AuditLogger $logger) {}

    public function created(Model $model): void
    {
        $this->record($model, 'create', null, $model->getAttributes());
    }

    public function updated(Model $model): void
    {
        $original = [];
        foreach ($model->getChanges() as $field => $new) {
            $original[$field] = $model->getRawOriginal($field);
        }
        $this->record($model, 'update', $original, $model->getChanges());
    }

    public function deleted(Model $model): void
    {
        $this->record($model, 'delete', $model->getAttributes(), null);
    }

    private function record(Model $model, string $verb, ?array $before, ?array $after): void
    {
        $type = strtolower(class_basename($model));       // User → users
        $this->logger->log(
            action: "{$type}.{$verb}",
            actorUserId: auth()->id(),
            companyId: auth()->user()?->active_company_id,
            resourceType: $type,
            resourceId: (string) $model->getKey(),
            dataBefore: $before,
            dataAfter: $after,
            actorIp: request()?->ip(),
        );
    }
}
