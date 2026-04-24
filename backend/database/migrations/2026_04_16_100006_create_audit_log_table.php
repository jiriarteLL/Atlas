<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Audit log inmutable (ADR-008 + no-negociable 9).
 *
 * Implementación: triggers DB que lanzan excepción ante UPDATE o DELETE,
 * garantizando inmutabilidad a nivel de motor independientemente del código.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('audit_log', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->timestampTz('at', 6)->useCurrent();     // precisión milis
            $table->uuid('actor_user_id')->nullable();
            $table->uuid('company_id')->nullable();
            $table->string('actor_ip', 45)->nullable();     // IPv6 cabe en 45
            $table->string('action');
            $table->string('resource_type')->nullable();
            $table->uuid('resource_id')->nullable();
            $table->jsonb('data_before')->nullable();
            $table->jsonb('data_after')->nullable();

            $table->index(['at'], 'idx_audit_at');
            $table->index(['actor_user_id', 'at'], 'idx_audit_actor');
            $table->index(['company_id', 'at'], 'idx_audit_company');
            $table->index(['resource_type', 'resource_id'], 'idx_audit_resource');
        });

        // Función + triggers que bloquean UPDATE y DELETE
        DB::unprepared(<<<'SQL'
            CREATE OR REPLACE FUNCTION audit_log_block_update_delete()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is INSERT-only';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER audit_log_no_update
                BEFORE UPDATE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION audit_log_block_update_delete();

            CREATE TRIGGER audit_log_no_delete
                BEFORE DELETE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION audit_log_block_update_delete();
        SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;
            DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;
            DROP FUNCTION IF EXISTS audit_log_block_update_delete();
        SQL);

        Schema::dropIfExists('audit_log');
    }
};
