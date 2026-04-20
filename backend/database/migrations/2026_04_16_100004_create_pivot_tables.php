<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // company_user: usuarios que pertenecen a empresas (M-N)
        Schema::create('company_user', function (Blueprint $table) {
            $table->uuid('company_id');
            $table->uuid('user_id');
            $table->jsonb('roles')->default('[]');
            $table->jsonb('permissions')->default('[]');
            $table->boolean('is_active')->default(true);
            $table->timestampsTz();

            $table->primary(['company_id', 'user_id']);
            $table->foreign('company_id')->references('id')->on('companies')->cascadeOnDelete();
            $table->foreign('user_id')->references('id')->on('users')->cascadeOnDelete();
        });

        // application_company: apps licenciadas a empresas (M-N)
        Schema::create('application_company', function (Blueprint $table) {
            $table->uuid('application_id');
            $table->uuid('company_id');
            $table->string('tier')->default('default');   // metadata sin logica V1 (DEC-018)
            $table->boolean('is_active')->default(true);
            $table->timestampTz('expires_at')->nullable();
            $table->timestampsTz();

            $table->primary(['application_id', 'company_id']);
            $table->foreign('application_id')->references('id')->on('applications')->cascadeOnDelete();
            $table->foreign('company_id')->references('id')->on('companies')->cascadeOnDelete();
        });

        // application_user: ternaria — acceso de usuario a app EN una empresa
        Schema::create('application_user', function (Blueprint $table) {
            $table->uuid('application_id');
            $table->uuid('user_id');
            $table->uuid('company_id');
            $table->jsonb('roles')->default('[]');
            $table->jsonb('permissions')->default('[]');
            $table->timestampsTz();

            $table->primary(['application_id', 'user_id', 'company_id']);
            $table->foreign('application_id')->references('id')->on('applications')->cascadeOnDelete();
            $table->foreign('user_id')->references('id')->on('users')->cascadeOnDelete();
            $table->foreign('company_id')->references('id')->on('companies')->cascadeOnDelete();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('application_user');
        Schema::dropIfExists('application_company');
        Schema::dropIfExists('company_user');
    }
};
