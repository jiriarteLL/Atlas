<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Application extends Model
{
    use HasFactory, HasUuids, SoftDeletes;

    protected $table = 'applications';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $fillable = [
        'name',
        'slug',
        'latest_version',
        'image_ref',
        'maestro_yaml',
        'webhook_secret_encrypted',
        'status',
    ];

    protected $hidden = ['webhook_secret_encrypted'];

    protected function casts(): array
    {
        return [
            'maestro_yaml' => 'array',
        ];
    }

    public function companies(): BelongsToMany
    {
        return $this->belongsToMany(Company::class, 'application_company')
            ->withPivot(['tier', 'is_active', 'expires_at'])
            ->withTimestamps();
    }

    public function users(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'application_user')
            ->withPivot(['roles', 'permissions', 'company_id'])
            ->withTimestamps();
    }
}
