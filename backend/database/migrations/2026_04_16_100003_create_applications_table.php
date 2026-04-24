<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('applications', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('name');
            $table->string('slug')->unique();
            $table->string('latest_version')->nullable();
            $table->string('image_ref')->nullable();
            $table->jsonb('maestro_yaml')->nullable();
            $table->text('webhook_secret_encrypted')->nullable();
            $table->enum('status', ['active', 'deprecated', 'retired'])->default('active');
            $table->timestampsTz();
            $table->softDeletesTz();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('applications');
    }
};
