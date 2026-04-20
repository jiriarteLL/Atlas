<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('instances', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->uuid('application_id');
            $table->uuid('company_id');
            $table->enum('status', [
                'provisioning', 'starting', 'healthy', 'degraded',
                'suspended', 'destroyed', 'purged', 'failed',
            ])->default('provisioning');
            $table->string('container_id')->nullable();
            $table->string('network_name');
            $table->string('db_host')->nullable();
            $table->string('db_name')->nullable();
            $table->string('db_user')->nullable();
            $table->text('db_password_encrypted')->nullable();
            $table->string('image_ref');
            $table->string('resources_memory')->default('512m');
            $table->string('resources_cpu')->default('0.5');
            $table->text('env_vars_encrypted')->nullable();
            $table->timestampTz('provisioned_at')->nullable();
            $table->timestampTz('last_healthy_at')->nullable();
            $table->timestampTz('destroyed_at')->nullable();
            $table->timestampTz('purge_eligible_at')->nullable();
            $table->timestampTz('purged_at')->nullable();
            $table->timestampsTz();

            $table->foreign('application_id')->references('id')->on('applications');
            $table->foreign('company_id')->references('id')->on('companies');

            $table->index(['company_id', 'application_id'], 'idx_instances_company_app');
            $table->index('status', 'idx_instances_status');
            $table->index('purge_eligible_at', 'idx_instances_purge_eligible');

            // Un solo registro activo por (app, company)
            $table->unique(['application_id', 'company_id'], 'uq_instances_app_company_active');
        });

        Schema::create('instance_health_history', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->uuid('instance_id');
            $table->timestampTz('at');
            $table->enum('status', ['ok', 'fail', 'timeout']);
            $table->integer('response_ms')->nullable();
            $table->integer('http_code')->nullable();
            $table->string('failure_reason')->nullable();

            $table->foreign('instance_id')->references('id')->on('instances')->cascadeOnDelete();
            $table->index(['instance_id', 'at'], 'idx_health_instance_at');
        });

        Schema::create('instance_lifecycle_events', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->uuid('instance_id');
            $table->timestampTz('at');
            $table->string('event_type');
            $table->string('previous_status')->nullable();
            $table->string('new_status');
            $table->jsonb('metadata')->nullable();

            $table->foreign('instance_id')->references('id')->on('instances')->cascadeOnDelete();
            $table->index(['instance_id', 'at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('instance_lifecycle_events');
        Schema::dropIfExists('instance_health_history');
        Schema::dropIfExists('instances');
    }
};
