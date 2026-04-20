<?php

declare(strict_types=1);

namespace App\Http\Controllers\Gateway;

use App\Models\Application;
use App\Models\Instance;
use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

/**
 * Gateway inter-apps (RF-080, RF-081).
 *
 * POST /api/v1/gateway/{target_app_slug}/{path+}
 *
 * Auth: headers X-Auth-* inyectados por Traefik ForwardAuth (la app origen ya está autenticada).
 * Reglas:
 *   - App origen y target deben pertenecer a la misma empresa activa.
 *   - User debe tener permiso 'gateway:{target_app_slug}' o '*'.
 *   - Comunicación directa entre redes Docker de apps está prohibida (ADR-007);
 *     el gateway es la única vía autorizada.
 *   - Cada llamada se registra en audit_log (action='gateway.forward').
 *   - Se firma con HMAC-SHA256 para que el target pueda verificar origen.
 */
class GatewayController
{
    public function __construct(private readonly AuditLogger $audit) {}

    public function __invoke(Request $request, string $targetSlug, string $path = ''): Response
    {
        $userId = $request->header('X-Auth-User-Id');
        $companyId = $request->header('X-Auth-Company-Id');
        $permissions = explode(',', (string) $request->header('X-Auth-Permissions', ''));

        if (! $userId || ! $companyId) {
            return response()->json([
                'error' => ['code' => 'AUTH_TOKEN_MISSING', 'message' => 'Missing X-Auth-* headers'],
            ], 401);
        }

        // Permisos: el user debe tener gateway:{target} o wildcard *
        $allowed = in_array('*', $permissions, true) || in_array("gateway:{$targetSlug}", $permissions, true);
        if (! $allowed) {
            $this->audit->log('gateway.forward.denied', actorUserId: $userId, companyId: $companyId,
                dataAfter: ['target' => $targetSlug, 'path' => $path]);
            return response()->json([
                'error' => ['code' => 'PERMISSION_DENIED', 'message' => "Falta permiso gateway:{$targetSlug}"],
            ], 403);
        }

        // Target app existe y licenciada a la misma empresa
        $targetApp = Application::where('slug', $targetSlug)->first();
        if (! $targetApp) {
            return response()->json([
                'error' => ['code' => 'RESOURCE_NOT_FOUND', 'message' => 'App target no existe'],
            ], 404);
        }

        $hasLicense = $targetApp->companies()
            ->where('companies.id', $companyId)
            ->where('application_company.is_active', true)
            ->exists();
        if (! $hasLicense) {
            return response()->json([
                'error' => ['code' => 'RESOURCE_CONFLICT', 'message' => 'App target no licenciada a esta empresa'],
            ], 409);
        }

        // Buscar instancia target healthy
        $instance = Instance::where('application_id', $targetApp->id)
            ->where('company_id', $companyId)
            ->whereIn('status', ['healthy', 'degraded'])
            ->first();
        if (! $instance) {
            return response()->json([
                'error' => ['code' => 'SERVICE_UNAVAILABLE', 'message' => 'Instancia target no disponible'],
            ], 503);
        }

        // Construir URL interna (Traefik ruteará por subdominio)
        $baseDomain = config('app.base_domain', 'maestro.local');
        $url = "https://{$targetApp->slug}-{$instance->company->subdomain}.{$baseDomain}".
               (str_starts_with($path, '/') ? $path : '/'.$path);

        // Firma HMAC para que el target verifique origen
        $webhookSecret = $targetApp->webhook_secret_encrypted
            ? Crypt::decryptString($targetApp->webhook_secret_encrypted)
            : null;

        $forwardId = (string) Str::ulid();
        $body = $request->getContent();
        $sourceApp = $request->header('X-Maestro-Source-App', 'unknown');

        $headers = [
            'X-Request-Id' => $request->header('X-Request-Id', $forwardId),
            'X-Maestro-Gateway' => 'true',
            'X-Maestro-Source-App' => $sourceApp,
            'X-Maestro-Forward-Id' => $forwardId,
            'X-Auth-User-Id' => $userId,
            'X-Auth-User-Email' => $request->header('X-Auth-User-Email', ''),
            'X-Auth-Company-Id' => $companyId,
            'X-Auth-Roles' => $request->header('X-Auth-Roles', ''),
            'X-Auth-Permissions' => $request->header('X-Auth-Permissions', ''),
            'Content-Type' => $request->header('Content-Type', 'application/json'),
        ];

        if ($webhookSecret) {
            $headers['X-Maestro-Gateway-Signature'] = hash_hmac('sha256', $body, $webhookSecret);
        }

        try {
            $upstream = Http::withHeaders($headers)
                ->timeout(30)
                ->withBody($body, $headers['Content-Type'])
                ->{strtolower($request->method())}($url);

            $this->audit->log(
                action: 'gateway.forward',
                actorUserId: $userId,
                companyId: $companyId,
                resourceType: 'instance',
                resourceId: $instance->id,
                dataAfter: [
                    'source_app' => $sourceApp,
                    'target' => $targetSlug,
                    'path' => $path,
                    'response_code' => $upstream->status(),
                ],
            );

            // Forward response
            return response($upstream->body(), $upstream->status())
                ->header('Content-Type', $upstream->header('Content-Type') ?: 'application/json')
                ->header('X-Maestro-Gateway', 'true')
                ->header('X-Maestro-Source-App', $targetSlug);
        } catch (\Throwable $e) {
            $this->audit->log('gateway.forward.failed', actorUserId: $userId, companyId: $companyId,
                dataAfter: ['target' => $targetSlug, 'error' => $e->getMessage()]);
            return response()->json([
                'error' => ['code' => 'SERVICE_UNAVAILABLE', 'message' => 'Target no responde'],
            ], 503);
        }
    }
}
