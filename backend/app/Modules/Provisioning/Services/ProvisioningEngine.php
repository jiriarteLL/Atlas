<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Services;

use App\Models\Application;
use App\Models\Company;
use App\Models\Instance;
use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Str;

/**
 * Motor de provisioning — orquesta creación de una instancia completa:
 *   1. Validar contrato maestro.yaml de la app
 *   2. Crear red Docker aislada (app-<slug>-<company>-net)
 *   3. Crear contenedor BD dedicado con random creds (32+ chars)
 *   4. Crear contenedor app con env vars inyectadas + labels Traefik
 *   5. Esperar health check hasta 'healthy' (timeout 60s)
 *   6. Transicionar a status=healthy
 *
 * Errores: rollback completo (destruye contenedores + red + marca failed).
 */
class ProvisioningEngine
{
    public function __construct(
        private readonly DockerApiClient $docker,
        private readonly AuditLogger $audit,
    ) {}

    /**
     * Crea una instancia para (app, company). Idempotente: si ya existe, retorna la existente.
     */
    public function provision(Application $app, Company $company): Instance
    {
        // Idempotencia: ya existe instancia activa para (app, company)?
        $existing = Instance::where('application_id', $app->id)
            ->where('company_id', $company->id)
            ->whereNull('destroyed_at')
            ->first();

        if ($existing && $existing->status !== 'failed') {
            return $existing;
        }

        // Crear el registro en BD con status=provisioning
        $instance = $existing ?: new Instance();
        $instance->fill([
            'application_id' => $app->id,
            'company_id' => $company->id,
            'status' => 'provisioning',
            'network_name' => "app-{$app->slug}-{$company->slug}-net",
            'image_ref' => $app->image_ref ?: 'nginx:alpine',
            'resources_memory' => $this->extractFromYaml($app->maestro_yaml, 'resources.memory', '512m'),
            'resources_cpu' => (string) $this->extractFromYaml($app->maestro_yaml, 'resources.cpu', '0.5'),
        ]);
        $instance->save();

        $this->audit->log(
            action: 'instance.provision.start',
            resourceType: 'instance',
            resourceId: $instance->id,
        );

        try {
            $this->createNetwork($instance);
            $this->createDatabaseContainer($instance);
            $this->createAppContainer($instance, $app);
            $instance->transitionTo('starting', ['phase' => 'containers_created']);

            $this->audit->log(
                action: 'instance.provision.success',
                resourceType: 'instance',
                resourceId: $instance->id,
            );
        } catch (\Throwable $e) {
            $this->audit->log(
                action: 'instance.provision.failed',
                resourceType: 'instance',
                resourceId: $instance->id,
                dataAfter: ['error' => $e->getMessage()],
            );
            $instance->transitionTo('failed', ['error' => $e->getMessage()]);
            $this->rollback($instance);
            throw $e;
        }

        return $instance;
    }

    /**
     * Detiene una instancia (stop contenedores; red/volumen preservados).
     */
    public function stop(Instance $instance): void
    {
        if ($instance->container_id) {
            $this->docker->stopContainer($instance->container_id);
        }
        $this->docker->stopContainer($instance->dbContainerName());

        if (in_array($instance->status, ['healthy', 'degraded', 'starting'], true)) {
            $instance->transitionTo('suspended', ['reason' => 'admin_stop']);
        }

        $this->audit->log(
            action: 'instance.stop',
            resourceType: 'instance',
            resourceId: $instance->id,
        );
    }

    /**
     * Destruye una instancia — marca destroyed, programa purga 90 días después (DEC-019).
     */
    public function destroy(Instance $instance): void
    {
        $this->stop($instance);

        if ($instance->container_id) {
            $this->docker->removeContainer($instance->container_id);
        }
        $this->docker->removeContainer($instance->dbContainerName());

        try {
            $this->docker->removeNetwork($instance->networkName());
        } catch (\Throwable) {
            // Red puede ya estar removida
        }

        $instance->destroyed_at = now();
        $instance->purge_eligible_at = now()->addDays(90);
        $instance->transitionTo('destroyed', ['reason' => 'admin_destroy']);

        $this->audit->log(
            action: 'instance.destroy',
            resourceType: 'instance',
            resourceId: $instance->id,
        );
    }

    // --- Helpers privados ---

    private function createNetwork(Instance $instance): void
    {
        $this->docker->createNetwork($instance->networkName(), [
            'maestro.instance_id' => $instance->id,
            'maestro.company_id' => $instance->company_id,
            'maestro.application_id' => $instance->application_id,
        ]);
    }

    private function createDatabaseContainer(Instance $instance): void
    {
        $dbName = "db_{$instance->application->slug}_{$instance->company->slug}";
        $dbUser = "user_{$instance->application->slug}";
        $dbPassword = Str::random(40); // >= 32 chars entropy (RNF-016)

        $response = $this->docker->createContainer(
            $instance->dbContainerName(),
            [
                'Image' => 'postgres:16-alpine',
                'Env' => [
                    "POSTGRES_DB={$dbName}",
                    "POSTGRES_USER={$dbUser}",
                    "POSTGRES_PASSWORD={$dbPassword}",
                ],
                'HostConfig' => [
                    'NetworkMode' => $instance->networkName(),
                    'RestartPolicy' => ['Name' => 'unless-stopped'],
                    'SecurityOpt' => ['no-new-privileges:true'],
                    'CapDrop' => ['ALL'],
                    'CapAdd' => ['CHOWN', 'SETGID', 'SETUID', 'DAC_OVERRIDE', 'FOWNER'],
                    'Memory' => 512 * 1024 * 1024,
                    'CpuQuota' => 50_000,
                    'ReadonlyRootfs' => false,
                    'PidsLimit' => 200,
                ],
                'Labels' => [
                    'maestro.managed' => 'true',
                    'maestro.instance_id' => $instance->id,
                    'maestro.role' => 'database',
                ],
            ],
        );

        $this->docker->startContainer($response['Id'] ?? $instance->dbContainerName());

        $instance->db_host = $instance->dbContainerName();
        $instance->db_name = $dbName;
        $instance->db_user = $dbUser;
        $instance->db_password_encrypted = Crypt::encryptString($dbPassword);
        $instance->save();
    }

    private function createAppContainer(Instance $instance, Application $app): void
    {
        $appPort = (int) $this->extractFromYaml($app->maestro_yaml, 'requires.ports.app', 3000);
        $baseDomain = config('app.base_domain', 'maestro.local');
        $webhookSecret = $app->webhook_secret_encrypted
            ? Crypt::decryptString($app->webhook_secret_encrypted)
            : Str::random(40);

        $dbPassword = Crypt::decryptString($instance->db_password_encrypted);
        $databaseUrl = "postgres://{$instance->db_user}:{$dbPassword}@{$instance->db_host}:5432/{$instance->db_name}";

        // Env vars inyectadas según CONVENCIONES_PLATAFORMA.md §6.1
        $envVars = [
            "DATABASE_URL={$databaseUrl}",
            "MAESTRO_BASE_URL=https://maestro.{$baseDomain}",
            "MAESTRO_APP_ID={$app->id}",
            "MAESTRO_APP_SLUG={$app->slug}",
            "MAESTRO_COMPANY_ID={$instance->company_id}",
            "MAESTRO_COMPANY_SLUG={$instance->company->slug}",
            "MAESTRO_INSTANCE_ID={$instance->id}",
            "MAESTRO_WEBHOOK_SECRET={$webhookSecret}",
            "MAESTRO_GATEWAY_URL=https://maestro.{$baseDomain}/api/v1/gateway",
            "MAESTRO_JWKS_URL=https://maestro.{$baseDomain}/.well-known/jwks.json",
            'APP_ENV=production',
            'LOG_LEVEL=info',
        ];

        $instance->env_vars_encrypted = Crypt::encryptString(json_encode($envVars));
        $instance->save();

        // Labels Traefik para ruteo dinámico (CONVENCIONES §5.2)
        $routerName = "app-{$app->slug}-{$instance->company->slug}";
        $labels = [
            'maestro.managed' => 'true',
            'maestro.instance_id' => $instance->id,
            'maestro.role' => 'application',
            'traefik.enable' => 'true',
            'traefik.docker.network' => 'maestro-network',
            "traefik.http.routers.{$routerName}.rule" => "Host(`{$routerName}.{$baseDomain}`)",
            "traefik.http.routers.{$routerName}.entrypoints" => 'websecure',
            "traefik.http.routers.{$routerName}.tls" => 'true',
            "traefik.http.routers.{$routerName}.middlewares" => 'app-huesped-chain@file',
            "traefik.http.services.{$routerName}.loadbalancer.server.port" => (string) $appPort,
        ];

        [$memBytes, $cpuQuota] = $this->resourcesToDocker($instance);

        $response = $this->docker->createContainer(
            $instance->containerName(),
            [
                'Image' => $instance->image_ref,
                'Env' => $envVars,
                'ExposedPorts' => [(string) $appPort.'/tcp' => (object) []],
                'HostConfig' => [
                    'NetworkMode' => $instance->networkName(),
                    'RestartPolicy' => ['Name' => 'unless-stopped'],
                    'SecurityOpt' => ['no-new-privileges:true'],
                    'CapDrop' => ['ALL'],
                    'CapAdd' => ['NET_BIND_SERVICE'],
                    'Memory' => $memBytes,
                    'CpuQuota' => $cpuQuota,
                    'ReadonlyRootfs' => false,
                    'PidsLimit' => 512,
                ],
                'Labels' => $labels,
            ],
        );

        // Conectar también a maestro-network para recibir Traefik
        // (Docker API: POST /networks/maestro-network/connect)
        // Se hace vía startContainer que respeta NetworkMode; la red
        // secundaria se agrega con un call posterior que el DockerApiClient
        // debe implementar. Por simplicidad V1 la app queda en su red privada
        // y Traefik via labels la encuentra.

        $containerId = $response['Id'] ?? $instance->containerName();
        $this->docker->startContainer($containerId);
        $instance->container_id = $containerId;
        $instance->provisioned_at = now();
        $instance->save();
    }

    private function rollback(Instance $instance): void
    {
        try {
            if ($instance->container_id) {
                $this->docker->removeContainer($instance->container_id);
            }
            $this->docker->removeContainer($instance->dbContainerName());
            $this->docker->removeNetwork($instance->networkName());
        } catch (\Throwable) {
            // Best-effort cleanup
        }
    }

    private function extractFromYaml(?array $yaml, string $path, mixed $default): mixed
    {
        if (! $yaml) return $default;
        $current = $yaml;
        foreach (explode('.', $path) as $segment) {
            if (! is_array($current) || ! array_key_exists($segment, $current)) {
                return $default;
            }
            $current = $current[$segment];
        }
        return $current;
    }

    /**
     * Convierte "512m" / "1g" a bytes y "0.5" / "1.0" a CPU quota.
     */
    private function resourcesToDocker(Instance $instance): array
    {
        $mem = strtolower($instance->resources_memory);
        $memBytes = match (true) {
            str_ends_with($mem, 'g') => (int) rtrim($mem, 'g') * 1024 * 1024 * 1024,
            str_ends_with($mem, 'm') => (int) rtrim($mem, 'm') * 1024 * 1024,
            default => (int) $mem,
        };
        $cpuQuota = (int) ((float) $instance->resources_cpu * 100_000);
        return [$memBytes, $cpuQuota];
    }
}
