<?php

declare(strict_types=1);

namespace App\Modules\AuditLog\Services;

use App\Models\AuditLog;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

class AuditLogger
{
    /**
     * Registra una acción en audit_log.
     * Campos sensibles (password, token, secret) son redactados.
     */
    public function log(
        string $action,
        ?string $actorUserId = null,
        ?string $companyId = null,
        ?string $resourceType = null,
        ?string $resourceId = null,
        ?array $dataBefore = null,
        ?array $dataAfter = null,
        ?string $actorIp = null,
    ): void {
        AuditLog::create([
            'at' => now(),
            'actor_user_id' => $actorUserId,
            'company_id' => $companyId,
            'actor_ip' => $actorIp,
            'action' => $action,
            'resource_type' => $resourceType,
            'resource_id' => $resourceId,
            'data_before' => $dataBefore ? $this->redact($dataBefore) : null,
            'data_after' => $dataAfter ? $this->redact($dataAfter) : null,
        ]);
    }

    public function logRequest(Request $request, Response $response): void
    {
        $route = $request->route();
        $action = $this->inferAction($request->method(), (string) ($route?->getName() ?? $request->path()));

        $this->log(
            action: $action,
            actorUserId: $request->user()?->id,
            companyId: $request->user()?->active_company_id,
            resourceType: $this->inferResourceType($request->path()),
            resourceId: $request->route('id') ? (string) $request->route('id') : null,
            dataBefore: null,
            dataAfter: $this->redact($request->all()),
            actorIp: $request->ip(),
        );
    }

    private function inferAction(string $method, string $routeOrPath): string
    {
        $verb = match ($method) {
            'POST' => 'create',
            'PATCH', 'PUT' => 'update',
            'DELETE' => 'delete',
            default => 'read',
        };

        // ej: "admin.companies.store" → "companies.create"
        $parts = explode('.', $routeOrPath);
        $resource = $parts[1] ?? $parts[0] ?? 'unknown';
        return Str::of($resource)->replace('/', '.')->toString().'.'.$verb;
    }

    private function inferResourceType(string $path): ?string
    {
        $segments = explode('/', trim($path, '/'));
        // api/admin/companies/{id} → companies
        return $segments[2] ?? $segments[1] ?? null;
    }

    /**
     * Redacta campos sensibles para cumplir RNF-013 + T-09.
     */
    private function redact(array $data): array
    {
        $sensitive = ['password', 'password_confirmation', 'token', 'secret', 'authorization', 'api_key'];
        $out = [];
        foreach ($data as $k => $v) {
            $keyLower = strtolower((string) $k);
            $isSensitive = false;
            foreach ($sensitive as $needle) {
                if (str_contains($keyLower, $needle)) {
                    $isSensitive = true;
                    break;
                }
            }
            if ($isSensitive) {
                $out[$k] = '[REDACTED]';
            } elseif (is_array($v)) {
                $out[$k] = $this->redact($v);
            } else {
                $out[$k] = $v;
            }
        }
        return $out;
    }
}
