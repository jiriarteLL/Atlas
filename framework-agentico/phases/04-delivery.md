# Fase 04 — Delivery

> **Proposito:** Empaquetar, configurar CI/CD y preparar el sistema para despliegue.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 04 (Delivery). Tu responsabilidad es empaquetar, configurar pipelines y preparar el sistema para despliegue.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.
Presta especial atencion a: git_workflow.permisos_de_merge, activacion_de_preset, validacion_transversal.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}

ESTADO DE GIT:
{context_packet.git}

AGENTES DISPONIBLES:
{context_packet.agents}

TU FLUJO:

1. EMPAQUETADO (Agent en worktree):
   Lanza agente de devops/infra para generar Dockerfile, docker-compose, .dockerignore.
   Constraints de Web Maestro en core/PRESET_WEB_MAESTRO.md seccion Fase 04.

2. CI/CD (Agent en worktree):
   Lanza agente para configurar pipeline y proteccion de ramas.

3. INTEGRACION:
   Lanza agente integrador para verificar compilacion, arranque, smoke tests, health check.

4. VALIDACION TRANSVERSAL:
   Segun RULES.md seccion validacion_transversal y framework-agentico/validation/TRANSVERSAL_TEMPLATE.md.

5. MERGE:
   Segun RULES.md seccion git_workflow.permisos_de_merge.

6. Devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Dockerfile generado y validado (compatible Web Maestro v4)
  - docker-compose funcional para desarrollo local
  - Pipeline CI/CD configurado
  - Sistema ensamblado compila y arranca
  - Smoke tests pasan
  - Health check verificado
  - Endpoint /maestro/branding responde 401 sin api key y 200 con api key valida
  - ENV vars obligatorias declaradas (DATABASE_URL, MAESTRO_API_KEY, SUPERADMIN_INITIAL_PASSWORD, APP_KEY/JWT_SECRET segun stack)
  - App registrada en el Maestro (URL, puerto, empresa_id, estado: active)
  - Validacion transversal aprobada
  - maestro.yaml validado contra schema v4 (auth_model: own, login_path, branding_url declarados)
```

---

## Artefactos Esperados

- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/deploy.yml`
- `.dockerignore`
- Checkpoint de fase

---

## Agentes Sugeridos

| Rol | Cuando | Modelo default |
|-----|--------|----------------|
| devops-engineer | Siempre | sonnet |
| integrator | Siempre | sonnet |
| ci-cd-specialist | Si el pipeline es complejo | sonnet |
