# Fase 06 — Retrospective

> **Proposito:** Cerrar el proyecto con retrospectiva, documentacion consolidada y mejora continua.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 06 (Retrospective). Tu responsabilidad es cerrar el proyecto con una retrospectiva completa y actualizar la memoria del framework.

CONTEXTO DEL PROYECTO:
{context_packet.project}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}

TU FLUJO:

1. CONSOLIDACION DE DOCUMENTACION:
   Lanza Agent(documentation-writer, sonnet) para:
   - Consolidar toda la documentacion del proyecto
   - Verificar que cada fase tenga su documentacion completa
   - Generar un indice maestro de documentacion
   - Generar README del proyecto actualizado

2. REPORTE FINAL:
   Lanza Agent(executive-reporter, sonnet) para:
   - Generar reporte ejecutivo del proyecto completo
   - Incluir: premisa, alcance, decisiones clave, metricas, costos
   - Formato para audiencia no tecnica

3. RETROSPECTIVA:
   Analiza el proyecto y documenta:
   - Que funciono bien? (patterns exitosos)
   - Que no funciono? (errores, blockers)
   - Que se puede mejorar? (para futuros proyectos)
   - Lecciones de integracion con Web Maestro

4. MEMORIA:
   Si hay lecciones que aplican a futuros proyectos, sugierelas al PM para que las registre en la memoria del framework.

5. Devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Retrospectiva completada y documentada
  - Documentacion del proyecto consolidada
  - Reporte final generado
  - Lecciones aprendidas registradas
  - Proyecto listo para marcar como completed
```

---

## Artefactos Esperados

- `docs/retrospective.md`
- `docs/final-report.md`
- `docs/README.md` (actualizado)
- Indice de documentacion consolidada
- Checkpoint de fase

---

## Agentes Sugeridos

| Rol | Cuando | Modelo default |
|-----|--------|----------------|
| documentation-writer | Siempre | sonnet |
| executive-reporter | Siempre | sonnet |
