# legacy/v3/

> Archivos deprecados del framework v3 / contrato `maestro.platform/v1`.
> Conservados como referencia historica. NO aplicar para proyectos nuevos.

---

## Contexto

En **framework v3 / contrato v1**, el modelo era:

- **Web Maestro = Identity Provider centralizado** (Laravel Passport + JWT + Microsoft Entra ID).
- Apps huesped consumian headers `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions` inyectados por Traefik ForwardAuth.
- **Multi-tenant logico**: `company_id` en cada tabla; las apps filtraban queries por tenant.
- **Sin login propio en las apps huesped**: prohibido implementar formulario de login, registro de usuarios, recuperacion de password, emision propia de tokens.
- Tabla `users` global en el Maestro (canonica).

En **framework v4 / contrato v2**, el modelo se invirtio:

- **Web Maestro = registry + redirector + provisioner** (no es IdP).
- **Auth propia de cada app huesped**: tabla `users`, login propio, tokens propios.
- **Single-tenant fisico**: un contenedor = una empresa, sin `company_id` en queries.
- Click en una app desde el portal abre URL en `target="_blank"` (no iframe, no inyeccion de identidad).
- Endpoint `/maestro/branding` autenticado con `X-Maestro-Api-Key` para que el Maestro lea nombre/logos de la empresa.

Detalle del cambio: `framework-agentico/CHANGELOG.md` v4.0 + `framework-agentico/migration/v3-to-v4.md`.

---

## Estructura

```
legacy/v3/
├── README.md                                                   (este archivo)
├── docs/
│   ├── APP_HUESPED_SPEC.md                                     (contrato v1)
│   ├── APP_HUESPED_BEST_PRACTICES.md                           (recomendaciones v1)
│   └── CONVENCIONES_PLATAFORMA.md                              (convenciones v1)
├── framework-agentico/
│   └── agents/
│       └── presets/
│           └── maestro-platform/
│               ├── PRESET.md                                   (preset v1 del Maestro)
│               └── rules/
│                   └── RULES.md                                (reglas v1 del Maestro)
├── PremisaWebMaestro/                                          (constitucion v1 del Maestro)
│   ├── 00-INDICE-MAESTRO.md
│   ├── 01-PREMISAS-Y-NO-NEGOCIABLES.md
│   ├── 02-MODELO-DE-DATOS.md
│   ├── 03-AUTENTICACION-Y-AUTORIZACION.md
│   ├── 04-INFRAESTRUCTURA-DOCKER.md
│   ├── 05-PORTAL-Y-RENDERIZADO.md
│   ├── 06-SDK-Y-CONTRATO.md
│   ├── 07-SISTEMA-AGENTICO.md
│   ├── 08-CICD-Y-GOBERNANZA.md
│   ├── 09-SEGURIDAD.md
│   ├── 10-OBSERVABILIDAD.md
│   └── 11-PLAN-DE-IMPLEMENTACION.md
└── arquitectura_actual.md                                      (snapshot historico 2026-04-14)
```

> **Nota:** la estructura fisica se materializa en la Fase 2 del proceso de saneamiento del framework v4 (los `git mv` se hacen en esa fase).

---

## Equivalentes vigentes (mapping legacy v3 -> v4)

| Documento legacy v3 | Equivalente vigente v4 |
|---|---|
| `legacy/v3/docs/APP_HUESPED_SPEC.md` | `docs/APP_HUESPED_SPEC.md` |
| `legacy/v3/docs/APP_HUESPED_BEST_PRACTICES.md` | `docs/APP_HUESPED_BEST_PRACTICES.md` |
| `legacy/v3/docs/CONVENCIONES_PLATAFORMA.md` | `docs/CONVENCIONES_PLATAFORMA.md` |
| `legacy/v3/framework-agentico/agents/presets/maestro-platform/PRESET.md` | `framework-agentico/agents/presets/maestro-platform/PRESET.md` |
| `legacy/v3/framework-agentico/agents/presets/maestro-platform/rules/RULES.md` | `framework-agentico/agents/presets/maestro-platform/rules/RULES.md` |
| `legacy/v3/PremisaWebMaestro/` | `PremisaWebMaestro/` (reescrita para v4) |
| `legacy/v3/arquitectura_actual.md` | (sin reemplazo; era snapshot historico) |
| (`mock/` que existia en v3) | (eliminado en v4; auth propia de la app no requiere mock) |

---

## Banner DEPRECADO en cada archivo

Cada `.md` bajo este directorio lleva en su encabezado:

```
> ⚠️ **DEPRECADO** - Documento del framework v3 / contrato `maestro.platform/v1`.
> Conservado como referencia historica.
>
> **Version vigente:** `<path al equivalente vigente>` o "no aplica" si fue eliminado.
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.
```

---

## Referencias

- `framework-agentico/CHANGELOG.md` v4.0 - detalle del cambio v3 -> v4.
- `framework-agentico/migration/v3-to-v4.md` - proceso de migracion para forks v3.
- `framework-agentico/migration/migrator-template.md` - template del Agent migrator.
