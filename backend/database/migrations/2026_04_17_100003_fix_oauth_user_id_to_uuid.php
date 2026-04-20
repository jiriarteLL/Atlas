<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Las migraciones de Passport v13 asumen user_id bigint. Nuestro User model usa UUID.
 * Esta migración altera oauth_access_tokens.user_id a UUID.
 */
return new class extends Migration
{
    public function up(): void
    {
        // Drop dependencies first
        DB::statement('DROP INDEX IF EXISTS oauth_access_tokens_user_id_index');

        Schema::table('oauth_access_tokens', function (Blueprint $table) {
            $table->dropColumn('user_id');
        });

        Schema::table('oauth_access_tokens', function (Blueprint $table) {
            $table->uuid('user_id')->nullable()->after('id');
            $table->index('user_id');
        });

        // También el device_codes si lo tiene
        if (Schema::hasColumn('oauth_device_codes', 'user_id')) {
            Schema::table('oauth_device_codes', function (Blueprint $table) {
                $table->dropColumn('user_id');
            });
            Schema::table('oauth_device_codes', function (Blueprint $table) {
                $table->uuid('user_id')->nullable()->after('id');
            });
        }

        // También auth_codes si lo tiene
        if (Schema::hasColumn('oauth_auth_codes', 'user_id')) {
            Schema::table('oauth_auth_codes', function (Blueprint $table) {
                $table->dropColumn('user_id');
            });
            Schema::table('oauth_auth_codes', function (Blueprint $table) {
                $table->uuid('user_id')->after('id');
            });
        }
    }

    public function down(): void
    {
        Schema::table('oauth_access_tokens', function (Blueprint $table) {
            $table->dropColumn('user_id');
        });
        Schema::table('oauth_access_tokens', function (Blueprint $table) {
            $table->foreignId('user_id')->nullable()->index()->after('id');
        });
    }
};
