<?php

declare(strict_types=1);

namespace Tests\Unit\Modules;

use App\Modules\Provisioning\Services\DockerApiClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class DockerApiClientTest extends TestCase
{
    public function test_create_network_llama_endpoint(): void
    {
        Http::fake([
            '*/networks/create' => Http::response(['Id' => 'net-123'], 201),
        ]);

        $client = new DockerApiClient('http://proxy:2375');
        $result = $client->createNetwork('my-net');

        $this->assertEquals('net-123', $result['Id']);
        Http::assertSent(fn ($r) => $r->url() === 'http://proxy:2375/networks/create');
    }

    public function test_remove_network(): void
    {
        Http::fake(['*/networks/my-net' => Http::response(null, 204)]);
        (new DockerApiClient('http://proxy:2375'))->removeNetwork('my-net');
        Http::assertSent(fn ($r) => $r->method() === 'DELETE');
    }

    public function test_create_container(): void
    {
        Http::fake([
            '*/containers/create*' => Http::response(['Id' => 'ctr-abc'], 201),
        ]);

        $client = new DockerApiClient('http://proxy:2375');
        $result = $client->createContainer('my-ctr', ['Image' => 'nginx']);

        $this->assertEquals('ctr-abc', $result['Id']);
    }

    public function test_start_stop_remove_inspect(): void
    {
        Http::fake([
            '*/containers/abc/start' => Http::response(null, 204),
            '*/containers/abc/stop*' => Http::response(null, 204),
            '*/containers/abc*' => Http::response(['Id' => 'abc', 'State' => ['Status' => 'running']], 200),
        ]);

        $client = new DockerApiClient('http://proxy:2375');
        $client->startContainer('abc');
        $client->stopContainer('abc');
        $inspected = $client->inspectContainer('abc');
        $this->assertEquals('abc', $inspected['Id']);
        $client->removeContainer('abc');
    }

    public function test_ping_exitoso(): void
    {
        Http::fake(['*/_ping' => Http::response('OK', 200)]);
        $this->assertTrue((new DockerApiClient('http://proxy:2375'))->ping());
    }

    public function test_ping_fallo_retorna_false(): void
    {
        Http::fake(['*/_ping' => fn () => throw new \RuntimeException('network')]);
        $this->assertFalse((new DockerApiClient('http://proxy:2375'))->ping());
    }

    public function test_list_containers_by_label(): void
    {
        Http::fake([
            '*/containers/json*' => Http::response([
                ['Id' => 'a', 'Labels' => ['maestro.managed' => 'true']],
            ], 200),
        ]);

        $client = new DockerApiClient('http://proxy:2375');
        $list = $client->listContainersByLabel('maestro.managed=true');
        $this->assertCount(1, $list);
    }
}
