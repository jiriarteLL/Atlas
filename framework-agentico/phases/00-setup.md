# Fase 00 — Setup

> **Proposito:** Garantizar que el entorno de desarrollo este funcional antes de arrancar.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 00 (Setup). Tu responsabilidad es verificar que el equipo tenga un entorno de desarrollo funcional para el proyecto.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

TU FLUJO:
1. Verifica prerequisitos del repositorio segun RULES.md seccion git_workflow.prerequisitos.
2. Diagnostica el entorno de desarrollo (herramientas del stack, Docker, BD, Web Maestro).
3. Verifica la plantilla Tailwise Bundle segun RULES.md seccion plantilla_base.
4. Si algo falta, genera instrucciones claras para el humano.
5. Actualiza el checkpoint de la fase con los resultados.

AGENTES: Esta fase normalmente no necesita sub-agentes. Si el diagnostico es complejo, podes lanzar un Agent(environment-checker, haiku) para verificar dependencias.

Al finalizar, devuelve un Phase Result segun core/CONTEXT_PACKET.md.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Repositorio accesible y estructura verificada
  - GitHub Issues HABILITADO (bloqueante si no lo esta)
  - Si fork: ramas del upstream identificadas y reportadas al PM
  - Herramientas del stack instaladas y funcionales
  - Docker (o analogo) instalado y funcional
  - Cliente de BD instalado y funcional
  - Acceso al repositorio verificado
  - Plantilla Tailwise Bundle verificada y variante identificada
  - Si Web Maestro: cuenta vinculada, repo generado, template intacto
```

---

## Artefactos Esperados

- Checkpoint de fase en `checkpoints/phases/00-setup.md`
- (Opcional) Lista de instrucciones pendientes para el humano

---

## Agentes Sugeridos

| Rol | Cuando | Modelo |
|-----|--------|--------|
| environment-checker | Si el diagnostico requiere ejecutar comandos | haiku |
