<?php

declare(strict_types=1);

namespace Tests\Unit\Middleware;

use App\Http\Middleware\EnforceCompanyIdFilter;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Request;
use Tests\TestCase;

class EnforceCompanyIdFilterTest extends TestCase
{
    use RefreshDatabase;

    public function test_permite_si_no_hay_body_company_id(): void
    {
        $company = $this->createCompany();
        $user = $this->createUser(['active_company_id' => $company->id]);
        $request = Request::create('/foo', 'POST', []);
        $request->setUserResolver(fn () => $user);

        $mw = new EnforceCompanyIdFilter();
        $response = $mw->handle($request, fn () => response()->json(['ok' => true]));

        $this->assertEquals(200, $response->getStatusCode());
    }

    public function test_rechaza_403_si_company_id_no_coincide(): void
    {
        $c1 = $this->createCompany();
        $c2 = $this->createCompany();
        $user = $this->createUser(['active_company_id' => $c1->id]);
        $request = Request::create('/foo', 'POST', ['company_id' => $c2->id]);
        $request->setUserResolver(fn () => $user);

        $mw = new EnforceCompanyIdFilter();
        $response = $mw->handle($request, fn () => response()->json(['ok' => true]));

        $this->assertEquals(403, $response->getStatusCode());
        $data = json_decode($response->getContent(), true);
        $this->assertEquals('AUTH_COMPANY_MISMATCH', $data['error']['code']);
    }

    public function test_permite_si_company_id_coincide(): void
    {
        $company = $this->createCompany();
        $user = $this->createUser(['active_company_id' => $company->id]);
        $request = Request::create('/foo', 'POST', ['company_id' => $company->id]);
        $request->setUserResolver(fn () => $user);

        $mw = new EnforceCompanyIdFilter();
        $response = $mw->handle($request, fn () => response()->json(['ok' => true]));

        $this->assertEquals(200, $response->getStatusCode());
    }
}
