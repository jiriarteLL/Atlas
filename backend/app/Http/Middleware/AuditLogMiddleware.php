<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Modules\AuditLog\Services\AuditLogger;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Loguea en audit_log cada acción administrativa (RF-020).
 * Se aplica al grupo /api/admin/*.
 */
class AuditLogMiddleware
{
    public function __construct(private readonly AuditLogger $logger) {}

    public function handle(Request $request, Closure $next): Response
    {
        /** @var Response $response */
        $response = $next($request);

        // Solo loguear métodos de escritura y solo si el status fue exitoso
        if (
            in_array($request->method(), ['POST', 'PATCH', 'PUT', 'DELETE'], true)
            && $response->getStatusCode() < 400
        ) {
            $this->logger->logRequest($request, $response);
        }

        return $response;
    }
}
