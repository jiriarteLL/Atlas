<?php

declare(strict_types=1);

namespace App\Http\Requests\Admin;

use Illuminate\Foundation\Http\FormRequest;

class StoreUserRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()?->is_platform_admin ?? false;
    }

    public function rules(): array
    {
        return [
            'email' => ['required', 'email', 'max:255', 'unique:users,email'],
            'display_name' => ['required', 'string', 'max:255'],
            'password' => ['nullable', 'string', 'min:12', 'max:255'],
            'is_platform_admin' => ['sometimes', 'boolean'],
            'memberships' => ['sometimes', 'array'],
            'memberships.*.company_id' => ['required', 'uuid', 'exists:companies,id'],
            'memberships.*.roles' => ['sometimes', 'array'],
            'memberships.*.permissions' => ['sometimes', 'array'],
            'memberships.*.is_active' => ['sometimes', 'boolean'],
        ];
    }
}
