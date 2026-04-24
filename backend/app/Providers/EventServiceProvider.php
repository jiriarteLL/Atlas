<?php

declare(strict_types=1);

namespace App\Providers;

use Illuminate\Foundation\Support\Providers\EventServiceProvider as ServiceProvider;

class EventServiceProvider extends ServiceProvider
{
    protected $listen = [
        // listeners se registran aqui o via #[AsEventListener] en Laravel 11+
    ];

    public function boot(): void
    {
        //
    }
}
