<?php

declare(strict_types=1);

use App\Http\Controllers\Auth\ForwardAuthController;
use App\Http\Controllers\Auth\LoginController;
use App\Http\Controllers\Auth\LogoutController;
use App\Http\Controllers\Auth\MeController;
use App\Http\Controllers\Auth\MicrosoftController;
use App\Http\Controllers\Auth\RefreshTokenController;
use App\Http\Controllers\Auth\SwitchCompanyController;
use Illuminate\Support\Facades\Route;

/*
|----------------------------------------------------------------------------
| Rutas de autenticacion — /api/auth/*
|
| Mount point: registradas en bootstrap/app.php dentro del grupo `api` con prefijo `api`.
|----------------------------------------------------------------------------
*/

Route::prefix('auth')->group(function () {

    // Login user/pass — rate limit 10/min/IP (RF-001)
    Route::post('/login', LoginController::class)
        ->middleware('throttle:10,1')
        ->name('auth.login');

    // Flujo Microsoft Entra ID (RF-002)
    Route::get('/microsoft/redirect', [MicrosoftController::class, 'redirect'])
        ->name('auth.microsoft.redirect');
    Route::get('/microsoft/callback', [MicrosoftController::class, 'callback'])
        ->name('auth.microsoft.callback');

    // Validacion de token consumida por Traefik ForwardAuth (RF-003)
    Route::get('/validate', ForwardAuthController::class)
        ->name('auth.validate');

    // Refresh (RF-004)
    Route::post('/refresh', RefreshTokenController::class)
        ->name('auth.refresh');

    // Logout (RF-005) — requiere auth
    Route::post('/logout', LogoutController::class)
        ->middleware('auth:api')
        ->name('auth.logout');

    // Cambio de empresa activa (RF-006) — requiere auth
    Route::post('/switch-company', SwitchCompanyController::class)
        ->middleware('auth:api')
        ->name('auth.switch-company');

    // Perfil del usuario autenticado
    Route::get('/me', MeController::class)
        ->middleware('auth:api')
        ->name('auth.me');
});
