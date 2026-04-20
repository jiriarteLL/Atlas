<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('hooks_deliveries', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->uuid('application_id');
            $table->uuid('company_id');
            $table->string('event_type');
            $table->jsonb('payload');
            $table->string('payload_hmac', 64)->nullable();
            $table->enum('status', ['pending', 'delivered', 'failed'])->default('pending');
            $table->integer('attempts')->default(0);
            $table->timestampTz('last_attempt_at')->nullable();
            $table->integer('last_response_code')->nullable();
            $table->string('last_failure_reason')->nullable();
            $table->timestampTz('created_at')->useCurrent();

            $table->foreign('application_id')->references('id')->on('applications');
            $table->foreign('company_id')->references('id')->on('companies');

            $table->index('status');
            $table->index(['application_id', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('hooks_deliveries');
    }
};
