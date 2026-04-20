<?php

return [
    'microsoft' => [
        'enabled' => (bool) env('MICROSOFT_ENTRA_ENABLED', false),
        'client_id' => env('MICROSOFT_ENTRA_CLIENT_ID'),
        'client_secret' => env('MICROSOFT_ENTRA_CLIENT_SECRET'),
        'redirect' => env('MICROSOFT_ENTRA_REDIRECT_URI'),
        'tenant' => env('MICROSOFT_ENTRA_TENANT_ID'),
        'auto_provision' => (bool) env('MICROSOFT_AUTO_PROVISION', false),
    ],
];
