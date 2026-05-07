# legacy/

> Archivos deprecados de versiones anteriores del framework agentico y de los contratos del Maestro.
> Conservados como referencia historica. NO aplicar para proyectos nuevos.

---

## Politica de versionado

- El path canonico (sin sufijo de version) siempre apunta a la version vigente.
- Cuando el framework bumpea de version mayor (ej: v4 -> v5), los archivos vigentes se mueven a `legacy/v{n}/` con banner DEPRECADO en su encabezado.
- El path canonico siempre apunta al actual; las versiones anteriores quedan navegables aqui.
- El git history preserva la evolucion completa; este directorio facilita revisar versiones anteriores sin recurrir a `git log`.

Detalle de la politica en `framework-agentico/core/RULES.md` seccion `politica_de_versionado`.

---

## Versiones disponibles

| Version | Path | Descripcion |
|---|---|---|
| v3 | [v3/](v3/README.md) | Modelo Maestro v1 (IdP centralizado, headers `X-Auth-*`, multi-tenant logico). Vigente hasta framework v3. |

---

## Cuando usar este directorio

- Si un fork tiene framework < v4 y el PO necesita entender el modelo viejo antes de migrar.
- Si el equipo necesita revisar decisiones de diseno historicas (auditoria, ADRs retrospectivos).
- Si el `framework-migrator` (ver `framework-agentico/migration/`) necesita comparar v{n} vs v{n+1}.

## Cuando NO usar este directorio

- Para proyectos nuevos. Siempre se aplican las versiones vigentes (paths canonicos).
- Para definir constraints de validadores. Los validadores leen unicamente los archivos vigentes.
- Para construir codigo. El codigo aspira a cumplir el modelo vigente, no el historico.

---

## Referencias

- `framework-agentico/CHANGELOG.md` - detalle de cambios entre versiones del framework.
- `framework-agentico/migration/` - templates y guias de migracion entre versiones.
- `framework-agentico/core/RULES.md` seccion `politica_de_versionado` - regla canonica.
