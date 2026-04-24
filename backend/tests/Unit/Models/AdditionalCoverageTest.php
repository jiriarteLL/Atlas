<?php

declare(strict_types=1);

namespace Tests\Unit\Models;

use App\Models\InstanceHealthHistory;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AdditionalCoverageTest extends TestCase
{
    use RefreshDatabase;

    public function test_company_users_relation(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $this->attachUserToCompany($user, $company);

        $this->assertCount(1, $company->users);
    }

    public function test_user_applications_in_company_relation(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $app = $this->makeApp();
        $app->users()->attach($user->id, [
            'company_id' => $company->id,
            'roles' => json_encode(['user']),
            'permissions' => json_encode(['read']),
        ]);

        $this->assertCount(1, $user->applicationsInCompany($company)->get());
    }

    public function test_instance_health_history_instance_relation(): void
    {
        $app = $this->makeApp();
        $company = $this->createCompany();
        $instance = $this->createInstance($app, $company);
        $record = InstanceHealthHistory::create([
            'instance_id' => $instance->id,
            'at' => now(),
            'status' => 'ok',
        ]);

        $this->assertEquals($instance->id, $record->instance->id);
    }
}
