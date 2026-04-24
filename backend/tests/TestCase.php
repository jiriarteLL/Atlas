<?php

declare(strict_types=1);

namespace Tests;

use App\Models\Application;
use App\Models\Company;
use App\Models\Instance;
use App\Models\User;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Laravel\Passport\Passport;

abstract class TestCase extends BaseTestCase
{
    protected function createPlatformAdmin(array $overrides = []): User
    {
        $u = User::create(array_merge([
            'email' => 'admin-'.Str::lower(Str::random(6)).'@test.local',
            'display_name' => 'Platform Admin',
            'password_hash' => Hash::make('secret_long_enough_12'),
            'is_platform_admin' => true,
        ], $overrides));
        return $u->fresh();
    }

    protected function createCompany(array $overrides = []): Company
    {
        $slug = 'c-'.Str::lower(Str::random(6));
        $c = Company::create(array_merge([
            'name' => 'Empresa '.Str::upper(Str::random(4)),
            'slug' => $slug,
            'subdomain' => $slug,
            'status' => 'active',
        ], $overrides));
        return $c->fresh();
    }

    protected function makeApp(array $overrides = []): Application
    {
        $slug = 'app-'.Str::lower(Str::random(6));
        $a = Application::create(array_merge([
            'name' => 'App '.Str::upper(Str::random(4)),
            'slug' => $slug,
            'latest_version' => '1.0.0',
            'image_ref' => 'registry/'.$slug.':1.0.0',
            'status' => 'active',
        ], $overrides));
        return $a->fresh();
    }

    public function createApplication(): \Illuminate\Foundation\Application
    {
        $app = require __DIR__.'/../bootstrap/app.php';
        $app->make(\Illuminate\Contracts\Console\Kernel::class)->bootstrap();
        return $app;
    }

    protected function createUser(array $overrides = []): User
    {
        $u = User::create(array_merge([
            'email' => 'u-'.Str::lower(Str::random(6)).'@test.local',
            'display_name' => 'User',
            'password_hash' => Hash::make('secret_long_enough_12'),
            'is_platform_admin' => false,
        ], $overrides));
        return $u->fresh();
    }

    protected function createInstance(Application $app, Company $company, array $overrides = []): Instance
    {
        $i = Instance::create(array_merge([
            'application_id' => $app->id,
            'company_id' => $company->id,
            'status' => 'healthy',
            'network_name' => 'net-'.Str::lower(Str::random(6)),
            'image_ref' => $app->image_ref ?? 'registry/'.$app->slug.':latest',
            'provisioned_at' => now(),
            'last_healthy_at' => now(),
        ], $overrides));
        return $i->fresh();
    }

    protected function actingAsPlatformAdmin(array $scopes = ['*']): User
    {
        $admin = $this->createPlatformAdmin();
        Passport::actingAs($admin, $scopes);
        return $admin;
    }

    protected function attachUserToCompany(User $user, Company $company, array $roles = ['admin'], array $permissions = ['*'], bool $active = true): void
    {
        $user->companies()->attach($company->id, [
            'roles' => json_encode($roles),
            'permissions' => json_encode($permissions),
            'is_active' => $active,
        ]);
    }

    protected function attachAppToCompany(Application $app, Company $company, bool $active = true, ?string $tier = 'standard'): void
    {
        $app->companies()->attach($company->id, [
            'tier' => $tier,
            'is_active' => $active,
            'expires_at' => now()->addYear(),
        ]);
    }
}
