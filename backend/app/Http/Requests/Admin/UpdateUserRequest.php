<?php

declare(strict_types=1);

namespace App\Http\Requests\Admin;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateUserRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()?->is_platform_admin ?? false;
    }

    public function rules(): array
    {
        $id = $this->route('id');
        return [
            'email' => ['sometimes', 'email', 'max:255', Rule::unique('users', 'email')->ignore($id)],
            'display_name' => ['sometimes', 'string', 'max:255'],
            'password' => ['nullable', 'string', 'min:12', 'max:255'],
            'is_platform_admin' => ['sometimes', 'boolean'],
            'active_company_id' => ['sometimes', 'nullable', 'uuid', 'exists:companies,id'],
        ];
    }
}
