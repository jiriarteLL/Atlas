<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\Application;
use App\Models\Company;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

/**
 * Seed de demo para Product Owner — iteración stabilization-1 (DEC-025).
 *
 * Idempotente: password se rehidrata si el usuario ya existe para que
 * `maestro:bootstrap-demo` sea reproducible sin `migrate:fresh`.
 */
class DemoPoSeeder extends Seeder
{
    public const COMPANY_SLUG = 'acme-demo';
    public const COMPANY_NAME = 'Acme Demo';

    public const PO_EMAIL = 'po@maestro.local';
    public const PO_PASSWORD = 'MaestroPO2026!';

    public const TESTER_EMAIL = 'tester@maestro.local';
    public const TESTER_PASSWORD = 'TesterMaestro2026!';

    public const DEMO_APP_SLUG = 'nginx-test';

    public function run(): void
    {
        $this->call(PassportClientsSeeder::class);

        $company = Company::firstOrCreate(
            ['slug' => self::COMPANY_SLUG],
            [
                'name' => self::COMPANY_NAME,
                'subdomain' => self::COMPANY_SLUG,
                'status' => 'active',
                'metadata' => ['created_by' => 'demo_po_seeder', 'purpose' => 'integration-tests'],
            ]
        );

        $po = $this->upsertUser(
            email: self::PO_EMAIL,
            password: self::PO_PASSWORD,
            displayName: 'Product Owner Demo',
            isPlatformAdmin: true,
            activeCompanyId: $company->id,
        );
        $this->attachMembership($po, $company->id, roles: ['admin'], permissions: ['*']);

        $tester = $this->upsertUser(
            email: self::TESTER_EMAIL,
            password: self::TESTER_PASSWORD,
            displayName: 'Tester Demo',
            isPlatformAdmin: false,
            activeCompanyId: $company->id,
        );
        $this->attachMembership($tester, $company->id, roles: ['user'], permissions: []);

        $app = Application::where('slug', self::DEMO_APP_SLUG)->first();
        if ($app) {
            $app->companies()->syncWithoutDetaching([
                $company->id => [
                    'tier' => 'demo',
                    'is_active' => true,
                    'expires_at' => null,
                ],
            ]);
            $app->users()->syncWithoutDetaching([
                $po->id => [
                    'roles' => json_encode(['admin']),
                    'permissions' => json_encode(['*']),
                    'company_id' => $company->id,
                ],
                $tester->id => [
                    'roles' => json_encode(['user']),
                    'permissions' => json_encode([]),
                    'company_id' => $company->id,
                ],
            ]);
        }

        $this->command->info('=== Demo PO seed completado ===');
        $this->command->warn('Empresa demo: '.self::COMPANY_NAME.' ('.self::COMPANY_SLUG.')');
        $this->command->warn('PO:     '.self::PO_EMAIL.' / '.self::PO_PASSWORD);
        $this->command->warn('Tester: '.self::TESTER_EMAIL.' / '.self::TESTER_PASSWORD);
        if (! $app) {
            $this->command->warn("App demo '".self::DEMO_APP_SLUG."' no registrada; asignación omitida.");
        }
    }

    private function upsertUser(
        string $email,
        string $password,
        string $displayName,
        bool $isPlatformAdmin,
        string $activeCompanyId,
    ): User {
        $user = User::firstOrCreate(
            ['email' => $email],
            [
                'display_name' => $displayName,
                'password_hash' => Hash::make($password),
                'is_platform_admin' => $isPlatformAdmin,
                'active_company_id' => $activeCompanyId,
            ]
        );

        if (! Hash::check($password, (string) $user->password_hash)) {
            $user->password_hash = Hash::make($password);
            $user->saveQuietly();
        }

        return $user;
    }

    /** @param list<string> $roles @param list<string> $permissions */
    private function attachMembership(User $user, string $companyId, array $roles, array $permissions): void
    {
        $user->companies()->syncWithoutDetaching([
            $companyId => [
                'roles' => json_encode($roles),
                'permissions' => json_encode($permissions),
                'is_active' => true,
            ],
        ]);
    }
}
