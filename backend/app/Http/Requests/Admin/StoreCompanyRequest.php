<?php

declare(strict_types=1);

namespace App\Http\Requests\Admin;

use Illuminate\Foundation\Http\FormRequest;

class StoreCompanyRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()?->is_platform_admin ?? false;
    }

    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:255'],
            'slug' => ['required', 'string', 'max:50', 'unique:companies,slug', 'regex:/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/'],
            'subdomain' => ['required', 'string', 'max:50', 'unique:companies,subdomain', 'regex:/^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/'],
            'status' => ['sometimes', 'in:active,suspended,inactive'],
            'metadata' => ['sometimes', 'array'],
        ];
    }
}
