<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('users', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('email')->unique();
            $table->string('password_hash')->nullable();
            $table->string('entra_id_sub')->nullable()->unique();
            $table->uuid('active_company_id')->nullable();
            $table->string('display_name');
            $table->boolean('is_platform_admin')->default(false);
            $table->timestampTz('last_login_at')->nullable();
            $table->timestampsTz();
            $table->softDeletesTz();

            $table->index('email');
            $table->index('entra_id_sub');
            $table->index('active_company_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('users');
    }
};
