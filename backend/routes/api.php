<?php

declare(strict_types=1);

use App\Http\Controllers\Admin\ApplicationsController;
use App\Http\Controllers\Admin\AuditLogController;
use App\Http\Controllers\Admin\CompaniesController;
use App\Http\Controllers\Admin\InstancesController;
use App\Http\Controllers\Admin\UsersController;
use App\Http\Controllers\Platform\HealthController;
use App\Http\Controllers\Platform\InventoryContextController;
use App\Http\Controllers\Platform\RegisterAppController;
use App\Http\Controllers\Portal\MyAppsController;
use App\Http\Controllers\Gateway\GatewayController;
use Illuminate\Support\Facades\Route;

/*
|----------------------------------------------------------------------------
| API routes — Maestro Platform V1
| Base URL: /api/*
| Auth rules:
|  - /api/platform/health y /api/.well-known/jwks.json → publico
|  - /api/v1/apps/register → header X-Maestro-App-Secret
|  - /api/v1/inventory/context → ForwardAuth (headers X-Auth-*)
|  - /api/admin/* → auth:api + is_platform_admin
|----------------------------------------------------------------------------
*/

// Publico sin auth
Route::prefix('platform')->group(function () {
    Route::get('/health', [HealthController::class, 'index'])->name('platform.health');
});

// API publica v1 (consumida por apps huesped y CI/CD)
Route::prefix('v1')->group(function () {
    Route::post('/apps/register', RegisterAppController::class)
        ->middleware('throttle:100,1')
        ->name('v1.apps.register');

    Route::get('/inventory/context', InventoryContextController::class)
        ->name('v1.inventory.context');

    // Gateway inter-apps (RF-080/081) — auth via ForwardAuth headers X-Auth-*
    Route::any('/gateway/{target_app}/{path}', GatewayController::class)
        ->where('path', '.*')
        ->name('v1.gateway');
});

// Portal API (para el user logueado en el portal React)
Route::prefix('portal')->middleware('auth:api')->group(function () {
    Route::get('/my-apps', MyAppsController::class)->name('portal.my-apps');
});

// Admin API (requiere Passport auth + is_platform_admin)
Route::prefix('admin')->middleware(['auth:api', 'audit_log'])->group(function () {
    // Companies CRUD (RF-010)
    Route::apiResource('companies', CompaniesController::class);

    // Users CRUD (RF-011)
    Route::apiResource('users', UsersController::class);

    // Applications CRUD (RF-012)
    Route::apiResource('applications', ApplicationsController::class);

    // Audit log (RF-021)
    Route::get('/audit-log', [AuditLogController::class, 'index'])
        ->name('admin.audit-log.index');

    // Instancias (Épica D — RF-030 a RF-034)
    Route::get('/instances', [InstancesController::class, 'index'])->name('admin.instances.index');
    Route::post('/instances', [InstancesController::class, 'store'])->name('admin.instances.store');
    Route::get('/instances/{id}', [InstancesController::class, 'show'])->name('admin.instances.show');
    Route::post('/instances/{id}/stop', [InstancesController::class, 'stop'])->name('admin.instances.stop');
    Route::post('/instances/{id}/start', [InstancesController::class, 'start'])->name('admin.instances.start');
    Route::post('/instances/{id}/restart', [InstancesController::class, 'restart'])->name('admin.instances.restart');
    Route::delete('/instances/{id}', [InstancesController::class, 'destroy'])->name('admin.instances.destroy');
    Route::post('/instances/{id}/restore', [InstancesController::class, 'restore'])->name('admin.instances.restore');
    Route::get('/instances/{id}/health-history', [InstancesController::class, 'healthHistory'])->name('admin.instances.health-history');
    Route::get('/instances/{id}/lifecycle-events', [InstancesController::class, 'lifecycleEvents'])->name('admin.instances.lifecycle-events');
});
