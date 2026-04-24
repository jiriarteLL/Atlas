<?php

declare(strict_types=1);

namespace Tests\Feature\AuditLog;

use App\Models\AuditLog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/**
 * Asserta el no-negociable 9: audit_log es INSERT-only a nivel DB y aplicación.
 * Corresponde a ADR-008 y mitigación M11 / T-11 del threat model.
 */
class AuditLogImmutabilityTest extends TestCase
{
    use RefreshDatabase;

    public function test_insert_works(): void
    {
        $log = AuditLog::create([
            'at' => now(),
            'action' => 'test.create',
            'resource_type' => 'test',
        ]);

        $this->assertDatabaseHas('audit_log', ['id' => $log->id, 'action' => 'test.create']);
    }

    public function test_update_via_eloquent_throws(): void
    {
        $log = AuditLog::create(['at' => now(), 'action' => 'test.create']);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('audit_log is INSERT-only');

        $log->update(['action' => 'hacked']);
    }

    public function test_update_via_raw_sql_throws_at_db_level(): void
    {
        $log = AuditLog::create(['at' => now(), 'action' => 'test.create']);

        $this->expectException(\Illuminate\Database\QueryException::class);
        DB::statement("UPDATE audit_log SET action = 'hacked' WHERE id = ?", [$log->id]);
    }

    public function test_delete_via_raw_sql_throws_at_db_level(): void
    {
        $log = AuditLog::create(['at' => now(), 'action' => 'test.create']);

        $this->expectException(\Illuminate\Database\QueryException::class);
        DB::statement('DELETE FROM audit_log WHERE id = ?', [$log->id]);
    }
}
