<?php

declare(strict_types=1);

namespace App\Http\Requests\Admin;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateCompanyRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()?->is_platform_admin ?? false;
    }

    public function rules(): array
    {
        $id = $this->route('id');
        return [
            'name' => ['sometimes', 'string', 'max:255'],
            'slug' => ['sometimes', 'string', 'max:50', Rule::unique('companies', 'slug')->ignore($id), 'regex:/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/'],
            'subdomain' => ['sometimes', 'string', 'max:50', Rule::unique('companies', 'subdomain')->ignore($id), 'regex:/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/'],
            'status' => ['sometimes', 'in:active,suspended,inactive'],
            'metadata' => ['sometimes', 'array'],
        ];
    }
}
