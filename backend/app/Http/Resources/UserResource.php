<?php

declare(strict_types=1);

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class UserResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'email' => $this->email,
            'display_name' => $this->display_name,
            'is_platform_admin' => (bool) $this->is_platform_admin,
            'active_company_id' => $this->active_company_id,
            'last_login_at' => $this->last_login_at?->toIso8601String(),
            'has_password' => ! is_null($this->password_hash),
            'has_microsoft_link' => ! is_null($this->entra_id_sub),
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
            'deleted_at' => $this->deleted_at?->toIso8601String(),
        ];
    }
}
