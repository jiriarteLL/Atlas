<?php

declare(strict_types=1);

namespace App\Http\Requests\Admin;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateApplicationRequest extends FormRequest
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
            'slug' => ['sometimes', 'string', 'max:50', Rule::unique('applications', 'slug')->ignore($id), 'regex:/^[a-z0-9][a-z0-9-]{2,49}$/'],
            'latest_version' => ['sometimes', 'nullable', 'string', 'regex:/^\d+\.\d+\.\d+$/'],
            'image_ref' => ['sometimes', 'nullable', 'string', 'max:255'],
            'maestro_yaml' => ['sometimes', 'nullable', 'array'],
            'status' => ['sometimes', 'in:active,deprecated,retired'],
        ];
    }
}
