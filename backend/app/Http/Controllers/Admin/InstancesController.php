<?php

declare(strict_types=1);

namespace App\Http\Controllers\Admin;

use App\Models\Application;
use App\Models\Company;
use App\Models\Instance;
use App\Modules\AuditLog\Services\AuditLogger;
use App\Modules\Provisioning\Jobs\ProvisionInstanceJob;
use App\Modules\Provisioning\Services\ProvisioningEngine;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class InstancesController
{
    public function __construct(
        private readonly ProvisioningEngine $engine,
        private readonly AuditLogger $audit,
    ) {}

    public function index(Request $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $query = Instance::with(['application:id,name,slug', 'company:id,name,slug']);

        if ($companyId = $request->string('company_id')->toString()) {
            $query->where('company_id', $companyId);
        }
        if ($appId = $request->string('application_id')->toString()) {
            $query->where('application_id', $appId);
        }
        if ($status = $request->string('status')->toString()) {
            $query->where('status', $status);
        }

        $instances = $query->orderBy('created_at', 'desc')
            ->cursorPaginate($request->integer('per_page', 20));

        return response()->json(['data' => $instances->items(), 'pagination' => [
            'cursor_next' => $instances->nextCursor()?->encode(),
            'cursor_prev' => $instances->previousCursor()?->encode(),
        ]]);
    }

    public function store(Request $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $validated = $request->validate([
            'application_id' => ['required', 'uuid', 'exists:applications,id'],
            'company_id' => ['required', 'uuid', 'exists:companies,id'],
        ]);

        // Verificar license activa
        $app = Application::findOrFail($validated['application_id']);
        $company = Company::findOrFail($validated['company_id']);

        $hasActiveLicense = $app->companies()
            ->where('companies.id', $company->id)
            ->wherePivot('is_active', true)
            ->exists();

        if (! $hasActiveLicense) {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_CONFLICT',
                    'message' => 'La aplicación no está licenciada para esta empresa.',
                ],
            ], 409);
        }

        // Conflicto: ya existe instancia activa
        $existing = Instance::where('application_id', $validated['application_id'])
            ->where('company_id', $validated['company_id'])
            ->whereNull('destroyed_at')
            ->first();
        if ($existing) {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_CONFLICT',
                    'message' => 'Ya existe una instancia activa para esta app+empresa.',
                    'details' => ['instance_id' => $existing->id],
                ],
            ], 409);
        }

        // Dispatch async
        ProvisionInstanceJob::dispatch($validated['application_id'], $validated['company_id'])
            ->onQueue('provisioning');

        $this->audit->log(
            action: 'instance.provision.dispatched',
            resourceType: 'instance',
            dataAfter: $validated,
        );

        return response()->json([
            'data' => [
                'message' => 'Provisioning dispatched',
                'application_id' => $validated['application_id'],
                'company_id' => $validated['company_id'],
                'status' => 'provisioning',
            ],
        ], Response::HTTP_ACCEPTED);
    }

    public function show(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::with(['application', 'company'])->findOrFail($id);
        return response()->json(['data' => $instance]);
    }

    public function stop(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);
        $this->engine->stop($instance);
        return response()->json(['data' => $instance->fresh()]);
    }

    public function start(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);

        if (! $instance->canTransitionTo('starting')) {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_CONFLICT',
                    'message' => "No se puede iniciar una instancia en estado {$instance->status}",
                ],
            ], 409);
        }

        // Simple: re-dispatch del job si estaba suspended
        ProvisionInstanceJob::dispatch($instance->application_id, $instance->company_id)
            ->onQueue('provisioning');

        $this->audit->log('instance.start.dispatched', resourceType: 'instance', resourceId: $instance->id);

        return response()->json(['data' => ['status' => 'starting']]);
    }

    public function restart(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);
        $this->engine->stop($instance);
        ProvisionInstanceJob::dispatch($instance->application_id, $instance->company_id)
            ->onQueue('provisioning');
        $this->audit->log('instance.restart', resourceType: 'instance', resourceId: $instance->id);
        return response()->json(['data' => ['status' => 'restarting']]);
    }

    public function destroy(Request $request, string $id): Response
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);
        $this->engine->destroy($instance);
        return response()->noContent();
    }

    public function restore(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);

        if ($instance->status !== 'destroyed') {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_CONFLICT',
                    'message' => 'Solo se pueden restaurar instancias destroyed dentro de su ventana de retención.',
                ],
            ], 409);
        }

        if ($instance->purged_at !== null) {
            return response()->json([
                'error' => [
                    'code' => 'RESOURCE_NOT_FOUND',
                    'message' => 'La instancia fue purgada y ya no se puede restaurar.',
                ],
            ], 404);
        }

        // Reset fields para re-provision
        $instance->destroyed_at = null;
        $instance->purge_eligible_at = null;
        $instance->status = 'provisioning';
        $instance->save();

        ProvisionInstanceJob::dispatch($instance->application_id, $instance->company_id)
            ->onQueue('provisioning');

        $this->audit->log('instance.restore', resourceType: 'instance', resourceId: $instance->id);

        return response()->json(['data' => $instance->fresh()]);
    }

    public function healthHistory(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);

        $query = $instance->healthHistory();
        if ($from = $request->date('from')) $query->where('at', '>=', $from);
        if ($to = $request->date('to')) $query->where('at', '<=', $to);

        $history = $query->orderBy('at', 'desc')
            ->limit($request->integer('limit', 200))
            ->get();

        return response()->json(['data' => $history]);
    }

    public function lifecycleEvents(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $instance = Instance::findOrFail($id);
        $events = $instance->lifecycleEvents()
            ->orderBy('at', 'desc')
            ->limit(100)
            ->get();
        return response()->json(['data' => $events]);
    }

    private function authorizePlatformAdmin(Request $request): void
    {
        if (! $request->user()?->is_platform_admin) {
            abort(403, 'Solo platform admin puede administrar instancias.');
        }
    }
}
