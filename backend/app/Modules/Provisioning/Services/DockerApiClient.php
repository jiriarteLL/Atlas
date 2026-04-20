<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Services;

use Illuminate\Support\Facades\Http;

/**
 * Cliente HTTP del docker-socket-proxy (ADR-006).
 *
 * Usa la allowlist restringida del proxy; CONTAINERS, NETWORKS, EXEC, INFO, VERSION.
 * NO tiene acceso a BUILD, VOLUMES, SYSTEM, SWARM.
 */
class DockerApiClient
{
    private readonly string $baseUrl;

    public function __construct(?string $baseUrl = null)
    {
        $this->baseUrl = rtrim($baseUrl ?? (string) env('DOCKER_PROXY_URL', 'http://maestro-docker-proxy:2375'), '/');
    }

    /**
     * Crea una red Docker dedicada para una instancia.
     */
    public function createNetwork(string $name, array $labels = []): array
    {
        return Http::post("{$this->baseUrl}/networks/create", [
            'Name' => $name,
            'Driver' => 'bridge',
            'Internal' => false,
            'Attachable' => true,
            'Labels' => array_merge([
                'maestro.managed' => 'true',
                'maestro.version' => config('app.version', 'dev'),
            ], $labels),
        ])->throw()->json();
    }

    public function removeNetwork(string $name): void
    {
        Http::delete("{$this->baseUrl}/networks/{$name}")->throw();
    }

    /**
     * Crea un contenedor con la configuración dada.
     */
    public function createContainer(string $name, array $config): array
    {
        return Http::post("{$this->baseUrl}/containers/create?name={$name}", $config)
            ->throw()
            ->json();
    }

    public function startContainer(string $id): void
    {
        Http::post("{$this->baseUrl}/containers/{$id}/start")->throw();
    }

    public function stopContainer(string $id, int $timeoutSeconds = 10): void
    {
        Http::post("{$this->baseUrl}/containers/{$id}/stop?t={$timeoutSeconds}");
        // No throw — puede estar ya detenido
    }

    public function removeContainer(string $id, bool $force = true, bool $removeVolumes = true): void
    {
        $q = http_build_query([
            'force' => $force ? 'true' : 'false',
            'v' => $removeVolumes ? 'true' : 'false',
        ]);
        Http::delete("{$this->baseUrl}/containers/{$id}?{$q}");
    }

    public function inspectContainer(string $id): array
    {
        return Http::get("{$this->baseUrl}/containers/{$id}/json")->throw()->json();
    }

    public function listContainersByLabel(string $label): array
    {
        $filters = json_encode(['label' => [$label]]);
        return Http::get("{$this->baseUrl}/containers/json?filters={$filters}&all=true")
            ->throw()
            ->json();
    }

    public function ping(): bool
    {
        try {
            return Http::timeout(2)->get("{$this->baseUrl}/_ping")->successful();
        } catch (\Throwable) {
            return false;
        }
    }
}
