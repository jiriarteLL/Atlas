<?php

declare(strict_types=1);

namespace Tests\Unit\Modules;

use App\Modules\Hooks\Jobs\DeliverHookJob;
use App\Modules\Hooks\Services\HookDispatcher;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Bus;
use Tests\TestCase;

class HookDispatcherTest extends TestCase
{
    use RefreshDatabase;

    public function test_on_user_added_despacha_job_para_cada_app_con_hook(): void
    {
        Bus::fake();

        $company = $this->createCompany();
        $user = $this->createUser();
        $appConHook = $this->makeApp([
            'slug' => 'con-hook',
            'maestro_yaml' => ['hooks' => ['on_user_added' => 'https://app.local/hook']],
        ]);
        $appSinHook = $this->makeApp(['slug' => 'sin-hook', 'maestro_yaml' => null]);

        $this->attachAppToCompany($appConHook, $company);
        $this->attachAppToCompany($appSinHook, $company);

        (new HookDispatcher())->onUserAdded($user, $company);

        Bus::assertDispatchedTimes(DeliverHookJob::class, 1);
    }

    public function test_on_user_removed_despacha_job(): void
    {
        Bus::fake();

        $company = $this->createCompany();
        $user = $this->createUser();
        $app = $this->makeApp([
            'slug' => 'app-x',
            'maestro_yaml' => ['hooks' => ['on_user_removed' => 'https://x.local/hook']],
        ]);
        $this->attachAppToCompany($app, $company);

        (new HookDispatcher())->onUserRemoved($user, $company);

        Bus::assertDispatched(DeliverHookJob::class);
    }

    public function test_on_license_granted_despacha_job(): void
    {
        Bus::fake();

        $company = $this->createCompany();
        $app = $this->makeApp([
            'slug' => 'app-lic',
            'maestro_yaml' => ['hooks' => ['on_company_license_granted' => 'https://x.local/lic']],
        ]);

        (new HookDispatcher())->onLicenseGranted($app, $company);

        Bus::assertDispatched(DeliverHookJob::class);
    }

    public function test_on_license_revoked_despacha_job(): void
    {
        Bus::fake();

        $company = $this->createCompany();
        $app = $this->makeApp([
            'slug' => 'app-rev',
            'maestro_yaml' => ['hooks' => ['on_company_license_revoked' => 'https://x.local/rev']],
        ]);

        (new HookDispatcher())->onLicenseRevoked($app, $company);

        Bus::assertDispatched(DeliverHookJob::class);
    }

    public function test_app_sin_endpoint_no_despacha(): void
    {
        Bus::fake();

        $company = $this->createCompany();
        $app = $this->makeApp(['slug' => 'app-nada', 'maestro_yaml' => ['hooks' => []]]);
        $this->attachAppToCompany($app, $company);

        (new HookDispatcher())->onUserAdded($this->createUser(), $company);

        Bus::assertNotDispatched(DeliverHookJob::class);
    }
}
