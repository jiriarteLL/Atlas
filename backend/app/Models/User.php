<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Passport\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, HasUuids, Notifiable, SoftDeletes;

    public $incrementing = false;

    protected $keyType = 'string';

    protected $fillable = [
        'email',
        'password_hash',
        'entra_id_sub',
        'active_company_id',
        'display_name',
        'is_platform_admin',
        'last_login_at',
    ];

    protected $hidden = [
        'password_hash',
    ];

    protected function casts(): array
    {
        return [
            'is_platform_admin' => 'boolean',
            'last_login_at' => 'datetime',
        ];
    }

    // --- Relaciones ---

    public function companies(): BelongsToMany
    {
        return $this->belongsToMany(Company::class, 'company_user')
            ->withPivot(['roles', 'permissions', 'is_active'])
            ->withTimestamps();
    }

    public function activeCompany(): BelongsTo
    {
        return $this->belongsTo(Company::class, 'active_company_id');
    }

    public function applicationsInCompany(Company $company): BelongsToMany
    {
        return $this->belongsToMany(Application::class, 'application_user')
            ->wherePivot('company_id', $company->id)
            ->withPivot(['roles', 'permissions', 'company_id'])
            ->withTimestamps();
    }

    // --- Helpers de autenticación ---

    public function getAuthPassword(): ?string
    {
        return $this->password_hash;
    }

    public function belongsTo_Company(string $companyId): bool
    {
        return $this->companies()->where('companies.id', $companyId)->exists();
    }

    public function rolesInCompany(string $companyId): array
    {
        $pivot = $this->companies()->where('companies.id', $companyId)->first()?->pivot;
        if (! $pivot || ! $pivot->is_active) {
            return [];
        }
        return is_array($pivot->roles) ? $pivot->roles : (json_decode($pivot->roles ?? '[]', true) ?: []);
    }

    public function permissionsInCompany(string $companyId): array
    {
        $pivot = $this->companies()->where('companies.id', $companyId)->first()?->pivot;
        if (! $pivot || ! $pivot->is_active) {
            return [];
        }
        return is_array($pivot->permissions) ? $pivot->permissions : (json_decode($pivot->permissions ?? '[]', true) ?: []);
    }
}
