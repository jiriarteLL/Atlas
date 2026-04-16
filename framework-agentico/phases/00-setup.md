# Fase 00 — Setup

> **Proposito:** Garantizar que el entorno de desarrollo este funcional antes de arrancar.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 00 (Setup). Tu responsabilidad es verificar que el equipo tenga un entorno de desarrollo funcional para el proyecto.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

TU FLUJO:
1. Diagnostica el entorno actual:
   - Verifica que el repositorio sea accesible y tenga la estructura esperada.
   - Verifica que las herramientas del stack esten instaladas (segun el stack definido).
   - Verifica Docker Desktop (o analogo) instalado y funcional.
   - Verifica acceso a base de datos.
   - Si aplica Web Maestro: verifica cuenta GitHub vinculada, repo generado, template intacto.

2. Si algo falta, genera instrucciones claras para el humano.

3. Actualiza el checkpoint de la fase con los resultados.

AGENTES: Esta fase normalmente no necesita sub-agentes. Si el diagnostico es complejo, podes lanzar un Agent(environment-checker, haiku) para verificar dependencias.

Al finalizar, devuelve un Phase Result segun core/CONTEXT_PACKET.md.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Repositorio accesible y estructura verificada
  - Herramientas del stack instaladas y funcionales
  - Docker (o analogo) instalado y funcional
  - Cliente de BD instalado y funcional
  - Acceso al repositorio verificado
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
