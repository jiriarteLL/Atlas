<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class InstanceHealthHistory extends Model
{
    protected $table = 'instance_health_history';

    public $timestamps = false;

    protected $fillable = [
        'instance_id', 'at', 'status', 'response_ms', 'http_code', 'failure_reason',
    ];

    protected function casts(): array
    {
        return ['at' => 'datetime'];
    }

    public function instance(): BelongsTo
    {
        return $this->belongsTo(Instance::class);
    }
}
