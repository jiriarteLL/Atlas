<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\Company;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // Passport Password Grant client (ISSUE-001 fix — Passport v13)
        $this->call(PassportClientsSeeder::class);

        // Tenant inicial (DEC-017)
        $company = Company::firstOrCreate(
            ['slug' => 'llyasoc'],
            [
                'name' => 'LLyAsoc Digital',
                'subdomain' => 'llyasoc',
                'status' => 'active',
                'metadata' => ['created_by' => 'seeder', 'initial_tenant' => true],
            ]
        );

        // Admin platform inicial
        $password = Str::random(24);
        $admin = User::firstOrCreate(
            ['email' => 'admin@llyasoc.com'],
            [
                'display_name' => 'Admin Maestro',
                'password_hash' => Hash::make($password),
                'is_platform_admin' => true,
                'active_company_id' => $company->id,
            ]
        );

        // Asignar al user a la empresa con rol admin
        $admin->companies()->syncWithoutDetaching([
            $company->id => [
                'roles' => json_encode(['admin']),
                'permissions' => json_encode(['*']),
                'is_active' => true,
            ],
        ]);

        $this->command->info('=== Maestro seed completado ===');
        $this->command->warn("Admin platform inicial: admin@llyasoc.com");
        $this->command->warn("Password temporal (rotar al primer login): {$password}");
    }
}
