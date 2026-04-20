<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use App\Models\AuditLog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Ramsey\Uuid\Uuid;
use Tests\TestCase;

class AuditLogControllerTest extends TestCase
{
    use RefreshDatabase;

    private function insertAudit(array $overrides = []): AuditLog
    {
        return AuditLog::create(array_merge([
            'at' => now(),
            'actor_user_id' => null,
            'company_id' => null,
            'action' => 'test.event',
            'resource_type' => 'test',
            'resource_id' => (string) Str::uuid(),
            'actor_ip' => '127.0.0.1',
            'data_before' => null,
            'data_after' => ['key' => 'value'],
        ], $overrides));
    }

    public function test_index_lista_audit_logs(): void
    {
        $this->actingAsPlatformAdmin();
        $this->insertAudit(['action' => 'auth.login.success']);

        $this->getJson('/api/admin/audit-log')
            ->assertStatus(200)
            ->assertJsonStructure(['data', 'meta', 'pagination']);
    }

    public function test_index_filtra_por_action(): void
    {
        $this->actingAsPlatformAdmin();
        $this->insertAudit(['action' => 'auth.login.success']);
        $this->insertAudit(['action' => 'auth.logout']);

        $response = $this->getJson('/api/admin/audit-log?action=auth.logout')->assertStatus(200);
        $actions = array_column($response->json('data'), 'action');
        $this->assertContains('auth.logout', $actions);
        $this->assertNotContains('auth.login.success', $actions);
    }

    public function test_index_filtra_por_resource_type(): void
    {
        $this->actingAsPlatformAdmin();
        $this->insertAudit(['resource_type' => 'company']);
        $this->insertAudit(['resource_type' => 'application']);

        $response = $this->getJson('/api/admin/audit-log?resource_type=company')->assertStatus(200);
        $types = array_column($response->json('data'), 'resource_type');
        $this->assertEquals(['company'], array_unique($types));
    }

    public function test_index_filtra_por_rango_fecha(): void
    {
        $this->actingAsPlatformAdmin();
        $this->insertAudit(['at' => now()->subDays(10), 'action' => 'old.event']);
        $this->insertAudit(['at' => now(), 'action' => 'new.event']);

        $response = $this->getJson('/api/admin/audit-log?from='.now()->subDay()->toDateString())
            ->assertStatus(200);
        $actions = array_column($response->json('data'), 'action');
        $this->assertNotContains('old.event', $actions);
        $this->assertContains('new.event', $actions);
    }

    public function test_non_admin_recibe_403(): void
    {
        $user = $this->createUser(['is_platform_admin' => false]);
        \Laravel\Passport\Passport::actingAs($user);
        $this->getJson('/api/admin/audit-log')->assertStatus(403);
    }
}
