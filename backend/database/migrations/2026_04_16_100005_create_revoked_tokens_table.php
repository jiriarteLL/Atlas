<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('revoked_tokens', function (Blueprint $table) {
            $table->string('jti')->primary();               // JWT ID
            $table->uuid('user_id');
            $table->timestampTz('revoked_at');
            $table->timestampTz('expires_at');

            $table->foreign('user_id')->references('id')->on('users')->cascadeOnDelete();
            $table->index('expires_at');                    // para purga diaria
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('revoked_tokens');
    }
};
