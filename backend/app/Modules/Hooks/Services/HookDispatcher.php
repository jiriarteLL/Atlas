<?php

declare(strict_types=1);

namespace App\Modules\Hooks\Services;

use App\Models\Application;
use App\Models\Company;
use App\Models\User;
use App\Modules\Hooks\Jobs\DeliverHookJob;
use Illuminate\Support\Str;

/**
 * Orquesta el envío de hooks salientes a las apps huésped.
 *
 * Cuando un evento ocurre en el Maestro (ej: user agregado a empresa),
 * para cada aplicación licenciada a esa empresa que declara el hook
 * correspondiente en su maestro.yaml, se despacha un DeliverHookJob.
 */
class HookDispatcher
{
    public function onUserAdded(User $user, Company $company): void
    {
        $this->dispatchForCompanyApps(
            eventType: 'on_user_added',
            company: $company,
            data: [
                'user_id' => $user->id,
                'email' => $user->email,
                'display_name' => $user->display_name,
                'company_id' => $company->id,
            ],
        );
    }

    public function onUserRemoved(User $user, Company $company): void
    {
        $this->dispatchForCompanyApps(
            eventType: 'on_user_removed',
            company: $company,
            data: [
                'user_id' => $user->id,
                'email' => $user->email,
                'company_id' => $company->id,
            ],
        );
    }

    public function onLicenseGranted(Application $app, Company $company): void
    {
        $this->dispatchForSingleApp(
            eventType: 'on_company_license_granted',
            app: $app,
            company: $company,
            data: [
                'company_id' => $company->id,
                'application_id' => $app->id,
            ],
        );
    }

    public function onLicenseRevoked(Application $app, Company $company): void
    {
        $this->dispatchForSingleApp(
            eventType: 'on_company_license_revoked',
            app: $app,
            company: $company,
            data: [
                'company_id' => $company->id,
                'application_id' => $app->id,
            ],
        );
    }

    private function dispatchForCompanyApps(string $eventType, Company $company, array $data): void
    {
        $apps = $company->applications()
            ->wherePivot('is_active', true)
            ->get();

        foreach ($apps as $app) {
            $this->dispatchForSingleApp($eventType, $app, $company, $data);
        }
    }

    private function dispatchForSingleApp(string $eventType, Application $app, Company $company, array $data): void
    {
        $endpoint = $app->maestro_yaml['hooks'][$eventType] ?? null;
        if (! $endpoint) {
            return;
        }

        DeliverHookJob::dispatch(
            applicationId: $app->id,
            companyId: $company->id,
            eventType: $eventType,
            endpoint: $endpoint,
            deliveryId: (string) Str::ulid(),
            payload: array_merge($data, [
                'event_type' => $eventType,
                'delivery_id' => (string) Str::ulid(),
                'timestamp' => now()->toIso8601String(),
            ]),
        )->onQueue('hooks');
    }
}
