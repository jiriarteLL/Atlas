<?php

declare(strict_types=1);

namespace App\Http\Controllers\Admin;

use App\Http\Requests\Admin\StoreUserRequest;
use App\Http\Requests\Admin\UpdateUserRequest;
use App\Http\Resources\UserResource;
use App\Models\Company;
use App\Models\User;
use App\Modules\Hooks\Services\HookDispatcher;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Symfony\Component\HttpFoundation\Response;

class UsersController
{
    public function __construct(private readonly HookDispatcher $hooks) {}

    public function index(Request $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $query = User::query();

        if ($companyId = $request->string('company_id')->toString()) {
            $query->whereHas('companies', fn ($q) => $q->where('companies.id', $companyId));
        }

        if ($request->has('is_platform_admin')) {
            $query->where('is_platform_admin', $request->boolean('is_platform_admin'));
        }

        if ($search = $request->string('search')->toString()) {
            $query->where(function ($q) use ($search) {
                $q->where('email', 'ilike', "%{$search}%")
                    ->orWhere('display_name', 'ilike', "%{$search}%");
            });
        }

        $users = $query->orderBy('created_at', 'desc')
            ->cursorPaginate($request->integer('per_page', 20));

        return UserResource::collection($users)->response();
    }

    public function store(StoreUserRequest $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $data = $request->validated();
        if (! empty($data['password'])) {
            $data['password_hash'] = Hash::make($data['password']);
        }
        unset($data['password'], $data['memberships']);

        $user = User::create($data);

        foreach ($request->input('memberships', []) as $membership) {
            $user->companies()->attach($membership['company_id'], [
                'roles' => json_encode($membership['roles'] ?? []),
                'permissions' => json_encode($membership['permissions'] ?? []),
                'is_active' => $membership['is_active'] ?? true,
            ]);

            // Dispatch hook on_user_added para apps de la empresa
            if ($company = Company::find($membership['company_id'])) {
                $this->hooks->onUserAdded($user, $company);
            }
        }

        return (new UserResource($user->fresh()))->response()->setStatusCode(201);
    }

    public function show(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $user = User::findOrFail($id);
        return (new UserResource($user))->response();
    }

    public function update(UpdateUserRequest $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $user = User::findOrFail($id);

        $data = $request->validated();
        if (! empty($data['password'])) {
            $data['password_hash'] = Hash::make($data['password']);
            unset($data['password']);
        }
        $user->update($data);

        return (new UserResource($user))->response();
    }

    public function destroy(Request $request, string $id): Response
    {
        $this->authorizePlatformAdmin($request);
        $user = User::findOrFail($id);

        // Disparar hook on_user_removed en cada empresa donde el user pertenecía
        foreach ($user->companies as $company) {
            $this->hooks->onUserRemoved($user, $company);
        }

        $user->delete();   // soft delete
        return response()->noContent();
    }

    private function authorizePlatformAdmin(Request $request): void
    {
        if (! $request->user()?->is_platform_admin) {
            abort(403, 'Solo platform admin puede administrar usuarios.');
        }
    }
}
