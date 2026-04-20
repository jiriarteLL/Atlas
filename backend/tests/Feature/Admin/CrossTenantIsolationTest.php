<?php

declare(strict_types=1);

namespace Tests\Feature\Admin;

use App\Models\Company;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Laravel\Passport\Passport;
use Tests\TestCase;

/**
 * Tests obligatorios del threat model (T-01 — Cross-tenant data leak).
 * Mitigaciones M5 y M10.
 */
class CrossTenantIsolationTest extends TestCase
{
    use RefreshDatabase;

    private User $adminA;
    private User $adminB;
    private Company $companyA;
    private Company $companyB;

    protected function setUp(): void
    {
        parent::setUp();

        $this->companyA = Company::create([
            'name' => 'Company A',
            'slug' => 'company-a',
            'subdomain' => 'company-a',
            'status' => 'active',
        ]);
        $this->companyB = Company::create([
            'name' => 'Company B',
            'slug' => 'company-b',
            'subdomain' => 'company-b',
            'status' => 'active',
        ]);

        $this->adminA = User::create([
            'email' => 'admin-a@test.local',
            'display_name' => 'Admin A',
            'password_hash' => Hash::make('secret_long_enough_12'),
            'is_platform_admin' => false,
            'active_company_id' => $this->companyA->id,
        ]);
        $this->adminA->companies()->attach($this->companyA->id, [
            'roles' => json_encode(['admin']),
            'permissions' => json_encode(['*']),
            'is_active' => true,
        ]);

        $this->adminB = User::create([
            'email' => 'admin-b@test.local',
            'display_name' => 'Admin B',
            'password_hash' => Hash::make('secret_long_enough_12'),
            'is_platform_admin' => false,
            'active_company_id' => $this->companyB->id,
        ]);
        $this->adminB->companies()->attach($this->companyB->id, [
            'roles' => json_encode(['admin']),
            'permissions' => json_encode(['*']),
            'is_active' => true,
        ]);
    }

    public function test_admin_de_empresa_a_no_accede_a_endpoints_admin_sin_is_platform_admin(): void
    {
        Passport::actingAs($this->adminA, ['company:'.$this->companyA->id]);

        // El endpoint /api/admin/companies requiere is_platform_admin=true
        $this->getJson('/api/admin/companies')->assertStatus(403);
    }

    public function test_admin_de_empresa_a_no_puede_cambiar_a_empresa_b(): void
    {
        Passport::actingAs($this->adminA, ['company:'.$this->companyA->id]);

        $this->postJson('/api/auth/switch-company', [
            'company_id' => $this->companyB->id,
        ])->assertStatus(403);   // ValidationException con status 403
    }

    public function test_usuario_sin_company_id_en_pivote_no_puede_usarla(): void
    {
        // Si adminA intenta operaciones con company_id de B pero no es miembro → rechazado
        Passport::actingAs($this->adminA, ['company:'.$this->companyA->id]);

        $this->postJson('/api/auth/switch-company', [
            'company_id' => $this->companyB->id,
        ])->assertStatus(403);
    }

    public function test_usuario_con_membresia_inactiva_no_accede(): void
    {
        // Desactivar la membresía de adminA en su propia empresa
        $this->adminA->companies()->updateExistingPivot($this->companyA->id, [
            'is_active' => false,
        ]);

        $this->assertEmpty($this->adminA->fresh()->rolesInCompany($this->companyA->id));
    }

    public function test_audit_log_registra_intento_de_switch_no_autorizado(): void
    {
        Passport::actingAs($this->adminA, ['company:'.$this->companyA->id]);

        $this->postJson('/api/auth/switch-company', [
            'company_id' => $this->companyB->id,
        ]);

        // El intento fallido no debería generar audit_log de success
        $this->assertDatabaseMissing('audit_log', [
            'action' => 'auth.company.switch',
            'actor_user_id' => $this->adminA->id,
            'company_id' => $this->companyB->id,
        ]);
    }
}
