<?php

declare(strict_types=1);

namespace App\Modules\Provisioning\Jobs;

use App\Models\Application;
use App\Models\Company;
use App\Modules\Provisioning\Services\ProvisioningEngine;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

/**
 * Job async que provisiona una instancia. Retries con backoff exponencial.
 */
class ProvisionInstanceJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 5;

    public function __construct(
        public readonly string $applicationId,
        public readonly string $companyId,
    ) {}

    public function backoff(): array
    {
        // 1s, 5s, 30s, 2m, 10m
        return [1, 5, 30, 120, 600];
    }

    public function handle(ProvisioningEngine $engine): void
    {
        $app = Application::findOrFail($this->applicationId);
        $company = Company::findOrFail($this->companyId);

        $engine->provision($app, $company);
    }
}
