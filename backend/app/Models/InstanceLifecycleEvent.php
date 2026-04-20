<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class InstanceLifecycleEvent extends Model
{
    protected $table = 'instance_lifecycle_events';

    public $timestamps = false;

    protected $fillable = [
        'instance_id', 'at', 'event_type', 'previous_status', 'new_status', 'metadata',
    ];

    protected function casts(): array
    {
        return [
            'at' => 'datetime',
            'metadata' => 'array',
        ];
    }

    public function instance(): BelongsTo
    {
        return $this->belongsTo(Instance::class);
    }
}
