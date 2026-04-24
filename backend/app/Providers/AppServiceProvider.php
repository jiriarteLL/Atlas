<?php

declare(strict_types=1);

namespace App\Providers;

use App\Models\Application as MaestroApplication;
use App\Models\Company;
use App\Models\User;
use App\Modules\AuditLog\Observers\AuditableObserver;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        // Strict mode: previene lazy loading accidental y queries sin índices.
        Model::shouldBeStrict(! app()->isProduction());
        Model::unguard();     // los modelos declaran $fillable/$guarded individualmente

        // Observer global para Audit Log en modelos críticos
        User::observe(AuditableObserver::class);
        Company::observe(AuditableObserver::class);
        MaestroApplication::observe(AuditableObserver::class);

        // RateLimiter: usado por throttleApi() en bootstrap/app.php (RNF-043)
        RateLimiter::for('api', fn (Request $r) => Limit::perMinute(
            (int) config('app.rate_limit_default_per_min', 1000)
        )->by($r->user()?->id ?: $r->ip()));
    }
}
