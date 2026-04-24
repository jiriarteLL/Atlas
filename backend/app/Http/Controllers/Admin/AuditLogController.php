<?php

declare(strict_types=1);

namespace App\Http\Controllers\Admin;

use App\Models\AuditLog;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AuditLogController
{
    public function index(Request $request): JsonResponse
    {
        if (! $request->user()?->is_platform_admin) {
            abort(403, 'Solo platform admin puede ver audit log.');
        }

        $query = AuditLog::query();

        if ($actor = $request->string('actor_user_id')->toString()) {
            $query->where('actor_user_id', $actor);
        }
        if ($companyId = $request->string('company_id')->toString()) {
            $query->where('company_id', $companyId);
        }
        if ($action = $request->string('action')->toString()) {
            $query->where('action', $action);
        }
        if ($resourceType = $request->string('resource_type')->toString()) {
            $query->where('resource_type', $resourceType);
        }
        if ($from = $request->date('from')) {
            $query->where('at', '>=', $from);
        }
        if ($to = $request->date('to')) {
            $query->where('at', '<=', $to);
        }

        $logs = $query->orderBy('at', 'desc')
            ->cursorPaginate($request->integer('per_page', 50));

        return response()->json([
            'data' => $logs->items(),
            'meta' => [
                'request_id' => $request->header('X-Request-Id'),
                'timestamp' => now()->toIso8601String(),
            ],
            'pagination' => [
                'cursor_next' => $logs->nextCursor()?->encode(),
                'cursor_prev' => $logs->previousCursor()?->encode(),
                'per_page' => $logs->perPage(),
            ],
        ]);
    }
}
