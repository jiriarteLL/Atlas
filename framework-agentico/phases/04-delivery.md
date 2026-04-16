# Fase 04 — Delivery

> **Proposito:** Empaquetar, configurar CI/CD y preparar el sistema para despliegue.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 04 (Delivery). Tu responsabilidad es empaquetar, configurar pipelines y preparar el sistema para despliegue.

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
   Lanza agente de devops/infra para:
   - Generar Dockerfile multi-stage, non-root, con HEALTHCHECK (Web Maestro obligatorio)
   - Generar docker-compose para desarrollo local
   - Configurar .dockerignore (excluir .git, node_modules, .env*, logs)
   - Validar maestro.yaml contra schema (si existe)

2. CI/CD (Agent en worktree):
   Lanza agente para:
   - Configurar pipeline en .github/workflows/deploy.yml
   - Configurar proteccion de rama main (PR + review)
   - Configurar checks automaticos (lint, tests, build)

3. INTEGRACION:
   Lanza agente integrador para:
   - Verificar que el sistema compila y arranca desde Docker
   - Correr smoke tests basicos
   - Verificar health check endpoint
   - Verificar coherencia entre todos los componentes

4. VALIDACION TRANSVERSAL (paralelo):
   Misma secuencia que en fase 03 — todos los validadores en paralelo.

5. Si todo aprueba, crea PR(s) hacia la epic branch.

6. Devuelve Phase Result al PM.

WEB MAESTRO OBLIGATORIO:
- Dockerfile: multi-stage, non-root, HEALTHCHECK
- NO --privileged, NO docker.sock
- NO puertos < 1024
- Pipeline en .github/workflows/deploy.yml
- maestro.yaml validado
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Dockerfile generado y validado (compatible Web Maestro)
  - docker-compose funcional para desarrollo local
  - Pipeline CI/CD configurado
  - Sistema ensamblado compila y arranca
  - Smoke tests pasan
  - Health check verificado
  - Validacion transversal aprobada
  - maestro.yaml validado (si existe)
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
