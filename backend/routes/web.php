<?php

use Illuminate\Support\Facades\Route;

// Maestro no sirve web views; el portal es SPA separado.
// Se mantiene este archivo porque Laravel lo espera.

Route::get('/', fn () => response()->json([
    'service' => 'Maestro Platform',
    'version' => config('app.version', 'dev'),
]));
