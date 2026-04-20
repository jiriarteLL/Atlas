<?php

declare(strict_types=1);

namespace App\Http\Controllers\Admin;

use App\Http\Requests\Admin\StoreCompanyRequest;
use App\Http\Requests\Admin\UpdateCompanyRequest;
use App\Http\Resources\CompanyResource;
use App\Models\Company;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class CompaniesController
{
    public function index(Request $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $query = Company::query();

        if ($search = $request->string('search')->toString()) {
            $query->where(function ($q) use ($search) {
                $q->where('name', 'ilike', "%{$search}%")
                    ->orWhere('slug', 'ilike', "%{$search}%");
            });
        }

        if ($status = $request->string('status')->toString()) {
            $query->where('status', $status);
        }

        $companies = $query->orderBy('created_at', 'desc')
            ->cursorPaginate($request->integer('per_page', 20));

        return CompanyResource::collection($companies)->response();
    }

    public function store(StoreCompanyRequest $request): JsonResponse
    {
        $this->authorizePlatformAdmin($request);

        $company = Company::create($request->validated());
        return (new CompanyResource($company))->response()->setStatusCode(201);
    }

    public function show(Request $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $company = Company::findOrFail($id);
        return (new CompanyResource($company))->response();
    }

    public function update(UpdateCompanyRequest $request, string $id): JsonResponse
    {
        $this->authorizePlatformAdmin($request);
        $company = Company::findOrFail($id);
        $company->update($request->validated());
        return (new CompanyResource($company))->response();
    }

    public function destroy(Request $request, string $id): Response
    {
        $this->authorizePlatformAdmin($request);
        $company = Company::findOrFail($id);
        $company->delete();   // soft delete
        return response()->noContent();
    }

    private function authorizePlatformAdmin(Request $request): void
    {
        if (! $request->user()?->is_platform_admin) {
            abort(403, 'Solo platform admin puede administrar empresas.');
        }
    }
}
