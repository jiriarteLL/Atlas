<?php

declare(strict_types=1);

namespace App\Http\Controllers\Platform;

use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;

class HealthController
{
    public function index(): JsonResponse
    {
        $checks = [
            'db' => $this->checkDb(),
            'redis' => $this->checkRedis(),
        ];

        $allOk = ! in_array(false, $checks, true);

        return response()->json([
            'status' => $allOk ? 'ok' : 'degraded',
            'checks' => array_map(fn ($v) => $v ? 'ok' : 'fail', $checks),
            'version' => config('app.version', 'dev'),
            'timestamp' => now()->toIso8601String(),
        ], $allOk ? 200 : 503);
    }

    private function checkDb(): bool
    {
        try {
            DB::connection()->getPdo();
            DB::select('SELECT 1');
            return true;
        } catch (\Throwable) {
            return false;
        }
    }

    private function checkRedis(): bool
    {
        try {
            return Redis::ping() !== false;
        } catch (\Throwable) {
            return false;
        }
    }
}
