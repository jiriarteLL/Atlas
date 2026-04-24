<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * Audit log es INSERT-only (triggers DB lo enforcan).
 * Este modelo deshabilita UPDATE/DELETE a nivel aplicación también como capa
 * extra de defensa (T-11 del threat model).
 */
class AuditLog extends Model
{
    protected $table = 'audit_log';

    public $timestamps = false;

    public const UPDATED_AT = null;
    public const CREATED_AT = 'at';

    protected $fillable = [
        'at',
        'actor_user_id',
        'company_id',
        'actor_ip',
        'action',
        'resource_type',
        'resource_id',
        'data_before',
        'data_after',
    ];

    protected function casts(): array
    {
        return [
            'at' => 'datetime',
            'data_before' => 'array',
            'data_after' => 'array',
        ];
    }

    public function save(array $options = []): bool
    {
        if ($this->exists) {
            throw new \RuntimeException('audit_log is INSERT-only');
        }
        return parent::save($options);
    }

    public function update(array $attributes = [], array $options = []): bool
    {
        throw new \RuntimeException('audit_log is INSERT-only');
    }

    public function delete(): ?bool
    {
        throw new \RuntimeException('audit_log is INSERT-only');
    }
}
