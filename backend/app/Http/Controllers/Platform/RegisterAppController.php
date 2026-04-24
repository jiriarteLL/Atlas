<?php

declare(strict_types=1);

namespace App\Http\Controllers\Platform;

use App\Models\Application;
use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\Yaml\Yaml;
use Symfony\Component\Yaml\Exception\ParseException;

/**
 * POST /api/v1/apps/register — Consumido por CI/CD de apps huésped al hacer push
 * de una nueva versión (RF-064, RF-070).
 *
 * Auth: header X-Maestro-App-Secret único por aplicación.
 */
class RegisterAppController
{
    public function __construct(private readonly AuditLogger $audit) {}

    public function __invoke(Request $request): JsonResponse
    {
        $secret = $request->header('X-Maestro-App-Secret');
        if (! $secret) {
            return response()->json([
                'error' => ['code' => 'AUTH_TOKEN_MISSING', 'message' => 'Missing X-Maestro-App-Secret'],
            ], 401);
        }

        $validated = $request->validate([
            'name' => ['required', 'string', 'max:50', 'regex:/^[a-z0-9][a-z0-9-]{2,49}$/'],
            'slug' => ['required', 'string', 'max:50', 'regex:/^[a-z0-9][a-z0-9-]{2,49}$/'],
            'version' => ['required', 'string', 'regex:/^\d+\.\d+\.\d+$/'],
            'image' => ['required', 'string', 'max:255'],
            'maestro_yaml' => ['required', 'string'],
        ]);

        // Localizar app por slug y validar el secret
        $app = Application::where('slug', $validated['slug'])->first();

        if (! $app) {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_NOT_FOUND',
                    'message' => 'Aplicación no registrada en el catálogo. Un admin debe crearla antes del primer registro automático.',
                ],
            ], 404);
        }

        // Verificar secret (comparación constant-time)
        $expected = decrypt($app->webhook_secret_encrypted ?? '');
        if (! hash_equals($expected, $secret)) {
            return response()->json([
                'error' => ['code' => 'AUTH_TOKEN_INVALID', 'message' => 'Invalid X-Maestro-App-Secret'],
            ], 401);
        }

        // Parsear maestro.yaml
        try {
            $yaml = Yaml::parse($validated['maestro_yaml']);
            $parsed = is_array($yaml)
                ? $yaml
                : throw new \RuntimeException('maestro_yaml no es un mapping válido');
        } catch (\Throwable $e) {
            return response()->json([
                'error' => [
                    'code' => 'CONTRACT_INVALID',
                    'message' => 'maestro.yaml no se puede parsear',
                    'details' => ['parse_error' => $e->getMessage()],
                ],
            ], 422);
        }

        // TODO Fase 03 siguiente iteración: validar contra JSON Schema oficial.

        $app->update([
            'latest_version' => $validated['version'],
            'image_ref' => $validated['image'],
            'maestro_yaml' => $parsed,
        ]);

        $this->audit->log(
            action: 'apps.register',
            resourceType: 'applications',
            resourceId: $app->id,
            dataAfter: ['version' => $validated['version'], 'image' => $validated['image']],
            actorIp: $request->ip(),
        );

        return response()->json(['data' => ['application' => $app->fresh()]], 200);
    }
}
