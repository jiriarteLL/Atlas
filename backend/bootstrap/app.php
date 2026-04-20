<?php

declare(strict_types=1);

use App\Http\Middleware\AuditLogMiddleware;
use App\Http\Middleware\EnforceCompanyIdFilter;
use App\Http\Middleware\RequestIdMiddleware;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        api: __DIR__.'/../routes/api.php',
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        then: function () {
            // Rutas de autenticación separadas para claridad
            Illuminate\Support\Facades\Route::middleware('api')
                ->prefix('api')
                ->group(__DIR__.'/../routes/auth.php');
        },
    )
    ->withMiddleware(function (Middleware $middleware) {
        // Middleware global que propaga el request_id (ULID) en toda la cadena.
        $middleware->append(RequestIdMiddleware::class);

        // Alias para middleware de módulos.
        $middleware->alias([
            'audit_log' => AuditLogMiddleware::class,
            'enforce_company' => EnforceCompanyIdFilter::class,
        ]);

        // Throttle customizado por endpoint.
        $middleware->throttleApi();
    })
    ->withExceptions(function (Exceptions $exceptions) {
        // Respuestas JSON estándar con code/message/details (API_CONTRACTS.md §1.4)
        $exceptions->render(function (Throwable $e, \Illuminate\Http\Request $request) {
            if (! $request->expectsJson() && ! str_starts_with($request->path(), 'api/')) {
                return null; // deja que el handler default maneje
            }

            $code = match (true) {
                $e instanceof \Illuminate\Auth\AuthenticationException => 'AUTH_TOKEN_MISSING',
                $e instanceof \Illuminate\Auth\Access\AuthorizationException => 'PERMISSION_DENIED',
                $e instanceof \Illuminate\Database\Eloquent\ModelNotFoundException => 'RESOURCE_NOT_FOUND',
                $e instanceof \Illuminate\Validation\ValidationException => 'VALIDATION_FAILED',
                $e instanceof \Symfony\Component\HttpKernel\Exception\ThrottleRequestsException => 'RATE_LIMIT_EXCEEDED',
                $e instanceof \Symfony\Component\HttpKernel\Exception\HttpException => match ($e->getStatusCode()) {
                    400 => 'BAD_REQUEST',
                    401 => 'AUTH_TOKEN_MISSING',
                    403 => 'PERMISSION_DENIED',
                    404 => 'RESOURCE_NOT_FOUND',
                    409 => 'CONFLICT',
                    422 => 'VALIDATION_FAILED',
                    429 => 'RATE_LIMIT_EXCEEDED',
                    default => 'HTTP_ERROR',
                },
                default => 'INTERNAL_ERROR',
            };

            $status = match (true) {
                $e instanceof \Symfony\Component\HttpKernel\Exception\HttpException => $e->getStatusCode(),
                $e instanceof \Illuminate\Validation\ValidationException => $e->status,
                default => match ($code) {
                    'AUTH_TOKEN_MISSING' => 401,
                    'PERMISSION_DENIED' => 403,
                    'RESOURCE_NOT_FOUND' => 404,
                    'VALIDATION_FAILED' => 422,
                    'RATE_LIMIT_EXCEEDED' => 429,
                    default => 500,
                },
            };

            // Si ValidationException tiene status 401/403, remapear code semanticamente.
            if ($e instanceof \Illuminate\Validation\ValidationException) {
                $code = match ($status) {
                    401 => 'AUTH_INVALID_CREDENTIALS',
                    403 => 'PERMISSION_DENIED',
                    default => $code,
                };
            }

            return response()->json([
                'error' => [
                    'code' => $code,
                    'message' => $e->getMessage() ?: 'Error',
                    'details' => $e instanceof \Illuminate\Validation\ValidationException
                        ? $e->errors()
                        : (object) [],
                ],
                'meta' => [
                    'request_id' => $request->header('X-Request-Id') ?? (string) \Symfony\Component\Uid\Ulid::generate(),
                    'timestamp' => now()->toIso8601String(),
                ],
            ], $status);
        });
    })->create();
