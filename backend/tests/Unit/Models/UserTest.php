<?php

declare(strict_types=1);

namespace Tests\Unit\Models;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class UserTest extends TestCase
{
    use RefreshDatabase;

    public function test_belongs_to_company(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $this->attachUserToCompany($user, $company);

        $this->assertTrue($user->fresh()->belongsTo_Company($company->id));
        $this->assertFalse($user->fresh()->belongsTo_Company('00000000-0000-0000-0000-000000000000'));
    }

    public function test_roles_in_company(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $this->attachUserToCompany($user, $company, ['admin', 'editor'], ['*'], true);

        $roles = $user->fresh()->rolesInCompany($company->id);
        $this->assertContains('admin', $roles);
        $this->assertContains('editor', $roles);
    }

    public function test_roles_in_company_pivote_inactivo_retorna_vacio(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $this->attachUserToCompany($user, $company, ['admin'], ['*'], false);

        $this->assertEquals([], $user->fresh()->rolesInCompany($company->id));
    }

    public function test_permissions_in_company(): void
    {
        $user = $this->createUser();
        $company = $this->createCompany();
        $this->attachUserToCompany($user, $company, ['viewer'], ['read:*', 'write:reports']);

        $perms = $user->fresh()->permissionsInCompany($company->id);
        $this->assertContains('read:*', $perms);
        $this->assertContains('write:reports', $perms);
    }

    public function test_permissions_sin_pivote_retorna_vacio(): void
    {
        $user = $this->createUser();
        $this->assertEquals([], $user->fresh()->permissionsInCompany('00000000-0000-0000-0000-000000000000'));
    }
}
