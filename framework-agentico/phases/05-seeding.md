# Fase 05 — Seeding

> **Proposito:** Garantizar que el MVP arranque con un usuario superadmin operativo (`admin@llyasoc.com`) creado de forma idempotente, listo para administrar la aplicacion.
> **Introducida en:** v4.0

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 05 (Seeding). Tu responsabilidad es asegurar que el seed
del superadmin (y opcionalmente usuarios adicionales decididos por el PO en Fase 02) se
implemente correctamente, sea idempotente y funcione bajo el preset Web Maestro v4.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.
Presta especial atencion a: validacion_transversal, preset_web_maestro.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}
(Lee especialmente {phases_dir}/02-seeding-plan.md y {phases_dir}/02-data-model.md)

ESTADO DE GIT:
{context_packet.git}

AGENTES DISPONIBLES:
{context_packet.agents}

INSTRUCCIONES DEL PM:
{context_packet.instructions}

TU FLUJO:

1. LECTURA DEL PLAN DE SEEDING:
   Lee 02-seeding-plan.md generado en Fase 02. Debe contener:
   - Superadmin obligatorio: admin@llyasoc.com con rol superadmin
   - Usuarios adicionales (opcionales): lista con email + rol
   - Catalogo de roles y permisos definido por la app

2. DESARROLLO DEL SEEDER (Agent en worktree):
   Lanza Agent(seeder-developer, sonnet) para implementar:
   - Seeder idempotente segun el stack (php artisan db:seed, npm run seed, etc.)
   - Lectura de SUPERADMIN_INITIAL_PASSWORD desde ENV
   - Validacion de password policy (>= 12 chars, complejidad). Si NO cumple, exit code != 0 sin crear nada.
   - Creacion / verificacion de rol "superadmin" con TODOS los permisos definidos por la app.
   - Creacion de admin@llyasoc.com si no existe; si existe, NO toca password, solo asegura que tenga rol superadmin.
   - Si el plan incluye usuarios adicionales: cada uno con su ENV var dedicada (ej. EDITOR_INITIAL_PASSWORD), misma logica idempotente.
   - Logs SIN passwords, SIN hashes, SIN api keys.
   - Hook en el pipeline de deploy para ejecutar el seeder despues de migrations.

3. TESTS DEL SEEDER (Agent en worktree):
   Lanza Agent(seeder-tester, sonnet) para implementar tests:
   - Test: SUPERADMIN_INITIAL_PASSWORD no seteada -> seeder falla con exit != 0.
   - Test: SUPERADMIN_INITIAL_PASSWORD debil -> seeder falla con exit != 0.
   - Test: Primera ejecucion -> crea admin@llyasoc.com con rol superadmin y todos los permisos.
   - Test: Segunda ejecucion (idempotencia) -> no duplica usuarios, no cambia password, no rompe.
   - Test: Si admin@llyasoc.com existe sin rol -> el seeder le asigna el rol superadmin.
   - Test: admin@llyasoc.com puede loguearse via /login con la password de la ENV.

4. MERGE WORKTREES + VALIDACION TRANSVERSAL:
   Mergea los worktrees a la issue branch. Lanza validadores en paralelo segun
   RULES.md seccion validacion_transversal. Validadores criticos para esta fase:
   - security-auditor: password storage seguro, no leakeo de SUPERADMIN_INITIAL_PASSWORD en logs.
   - qa-tester: tests del seeder pasando (incluye idempotencia).
   - compliance-analyst: password policy + audit log de auth + creacion del superadmin documentada.

5. VEREDICTO Y MERGE:
   Segun RULES.md seccion validacion_transversal.veredicto y git_workflow.permisos_de_merge.

6. EJECUCION DEL SEED:
   Antes de cerrar la fase, el orquestador (o un agente delegado) ejecuta el seed
   contra la BD del entorno de validacion (no produccion). Confirma que:
   - admin@llyasoc.com aparece en la BD.
   - El usuario tiene el rol superadmin con todos los permisos.
   - El usuario puede loguearse via /login.

7. Devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Seeder idempotente implementado en el stack del proyecto
  - SUPERADMIN_INITIAL_PASSWORD validada por password policy en runtime (no hardcoded)
  - admin@llyasoc.com creado en BD con rol superadmin y TODOS los permisos definidos por la app
  - Re-ejecucion del seeder NO duplica usuarios ni cambia passwords existentes
  - Logs del seeder no filtran password, hash ni api keys
  - Tests del seeder pasando (no seteo, password debil, primer run, segundo run, asignacion de rol faltante, login exitoso)
  - Hook del seeder integrado en el pipeline de deploy (post-migrations)
  - Si hay usuarios adicionales (segun 02-seeding-plan.md): tambien creados de forma idempotente
  - Validacion transversal aprobada
  - Issue de seeding cerrado en GitHub
```

---

## Artefactos Esperados

- Codigo del seeder (segun convencion del stack: `database/seeders/SuperAdminSeeder.php`, `prisma/seed.ts`, `src/seeds/superadmin.ts`, etc.)
- Tests del seeder (`tests/Feature/SuperAdminSeederTest.php`, `__tests__/seed.test.ts`, etc.)
- Documentacion en `docs/seeding.md` (como ejecutar, que ENV vars necesita, como rotar la password despues del primer login)
- Hook de pipeline en `.github/workflows/deploy.yml` (paso post-migrations: ejecutar el seeder)
- Checkpoint de fase

---

## Agentes Sugeridos

| Rol | Cuando | Modelo default |
|-----|--------|----------------|
| seeder-developer | Siempre | sonnet |
| seeder-tester | Siempre | sonnet |
| security-auditor | Siempre (validador) | sonnet |
| qa-tester | Siempre (validador) | sonnet |
| compliance-analyst | Siempre (validador) | sonnet |

---

## Contraindicaciones

- **NO** usar passwords default (`admin`, `password`, `12345`, etc.). Si `SUPERADMIN_INITIAL_PASSWORD` cae en una blacklist de passwords comunes, el seeder DEBE fallar.
- **NO** loggear `SUPERADMIN_INITIAL_PASSWORD`, `MAESTRO_API_KEY`, ni el hash resultante.
- **NO** modificar la password de un superadmin ya existente desde el seeder. Cualquier cambio post-creacion debe ocurrir desde la UI/API de la app, no desde el seeder.
- **NO** sembrar usuarios adicionales sin una decision explicita del PO documentada en `02-seeding-plan.md`.
