<?php

declare(strict_types=1);

namespace App\Http\Controllers\Admin;

use App\Http\Requests\Admin\StoreApplicationRequest;
use App\Http\Requests\Admin\UpdateApplicationRequest;
use App\Http\Resources\ApplicationResource;
use App\Models\Application;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class ApplicationsController
{
    public function index(Request $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $apps = Application::query()
            ->orderBy('created_at', 'desc')
            ->cursorPaginate($request->integer('per_page', 20));

        return ApplicationResource::collection($apps)->response();
    }

    public function store(StoreApplicationRequest $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $app = Application::create($request->validated());
        return (new ApplicationResource($app))->response()->setStatusCode(201);
    }

    public function show(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $app = Application::findOrFail($id);
        return (new ApplicationResource($app))->response();
    }

    public function update(UpdateApplicationRequest $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $app = Application::findOrFail($id);
        $app->update($request->validated());
        return (new ApplicationResource($app))->response();
    }

    public function destroy(Request $request, string $id): Response
    {
        $this->authorizePlatformAdmin($request);
        $app = Application::findOrFail($id);
        $app->delete();
        return response()->noContent();
    }

    private function authorizePlatformAdmin(Request $request): void
    {
        if (! $request->user()?->is_platform_admin) {
            abort(403, 'Solo platform admin puede administrar aplicaciones.');
        }
    }
}
