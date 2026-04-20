Activa tu rol de Project Manager (PM) para generar un REPORTE EJECUTIVO.

Lee estos archivos:
- `framework-agentico/core/PM.md` (tu system prompt)
- `framework-agentico/checkpoints/GLOBAL.md` (estado del proyecto)
- `framework-agentico/cost/COST_LOG.md` (metricas de consumo)
- Checkpoints de fases completadas en `framework-agentico/checkpoints/phases/`

Genera un reporte ejecutivo que incluya:
1. Resumen del proyecto (premisa, alcance, stack)
2. Progreso por fase (completadas, en curso, pendientes)
3. Metricas de calidad (validaciones transversales, issues cerrados)
4. Metricas de costo (tokens consumidos, costo estimado, eficiencia)
5. Riesgos y escalaciones pendientes
6. Proximos pasos

Formato: orientado a audiencia no tecnica (Product Owner).
Si necesitas mas detalle, lanza Agent(executive-reporter, sonnet) para generarlo.

Habla en espanol.
