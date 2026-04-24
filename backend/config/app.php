<?php

return [
    'name' => env('APP_NAME', 'Maestro'),
    'env' => env('APP_ENV', 'production'),
    'debug' => (bool) env('APP_DEBUG', false),
    'url' => env('APP_URL', 'https://maestro.maestro.local'),
    'timezone' => env('APP_TIMEZONE', 'America/Argentina/Buenos_Aires'),
    'locale' => env('APP_LOCALE', 'es_AR'),
    'fallback_locale' => env('APP_FALLBACK_LOCALE', 'es'),
    'faker_locale' => env('APP_FAKER_LOCALE', 'es_AR'),
    'cipher' => 'AES-256-CBC',
    'key' => env('APP_KEY'),
    'previous_keys' => [...array_filter(explode(',', (string) env('APP_PREVIOUS_KEYS')))],
    'maintenance' => [
        'driver' => env('APP_MAINTENANCE_DRIVER', 'file'),
        'store' => env('APP_MAINTENANCE_STORE', 'database'),
    ],
    'base_domain' => env('MAESTRO_BASE_DOMAIN', 'maestro.local'),
    'encryption_key' => env('MAESTRO_ENCRYPTION_KEY'),
    'version' => '1.0.0-dev',
];
