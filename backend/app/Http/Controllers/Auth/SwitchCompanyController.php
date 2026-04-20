<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Auth\Services\TokenIssuer;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;

class SwitchCompanyController
{
    public function __construct(
        private readonly TokenIssuer $issuer,
        private readonly AuditLogger $audit,
    ) {}

    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'company_id' => ['required', 'uuid'],
        ]);

        $user = $request->user();

        if (! $user->belongsTo_Company($validated['company_id'])) {
            throw ValidationException::withMessages([
                'company_id' => 'El usuario no pertenece a esta empresa.',
            ])->status(403);
        }

        $user->active_company_id = $validated['company_id'];
        $user->saveQuietly();

        $payload = $this->issuer->issueForUser($user, $validated['company_id']);

        $this->audit->log(
            action: 'auth.company.switch',
            actorUserId: $user->id,
            companyId: $validated['company_id'],
            actorIp: $request->ip(),
            dataAfter: ['company_id' => $validated['company_id']],
        );

        return response()->json(['data' => $payload]);
    }
}
