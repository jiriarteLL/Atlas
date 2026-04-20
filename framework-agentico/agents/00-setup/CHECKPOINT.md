# Checkpoint Fase 00 — Setup

```yaml
status: "completed"
updated_at: "2026-04-16"

exit_criteria_redefinidos_por_DEC-012:
  ide_installed: true           # VSCode Server via WSL extension
  docker_installed: true        # Docker 29.4.0 + Compose v5.1.1
  docker_daemon_running: true   # server version responde
  git_installed: true           # git 2.43.0
  repo_access_verified: true    # git ls-remote origin HEAD responde (SHA 2b88f4d)
  db_client_host: "opcional"    # se acepta cliente grafico en Windows (DBeaver/DataGrip/TablePlus) o psql ephemeral via contenedor
  maestro_linked: "no_aplica"   # este proyecto construye el Maestro, no es app huesped

exit_criteria_descartados_por_DEC-012:
  php_installed_host: "descartado — se usa imagen php:8.3-cli"
  composer_installed_host: "descartado — se invoca via docker compose run --rm"
  node_installed_host: "descartado — se usa imagen node:20-alpine"
  psql_installed_host: "descartado — se usa imagen postgres:16-alpine"

environment:
  os: "Ubuntu 24.04.1 LTS (Noble Numbat) en WSL2 sobre Windows (kernel 6.6.87.2-microsoft-standard-WSL2)"
  ide: "VSCode Server (remote WSL)"
  ide_version: "41dd792b (build instalado en ~/.vscode-server)"
  docker_version: "29.4.0"
  docker_compose_version: "v5.1.1"
  git_version: "2.43.0"
  gh_cli: "instalado"
  db_client_host: "DBeaver en Windows host (confirmado 2026-04-16)"
  runtime_strategy: "100% dockerizado (DEC-012) — ningun runtime instalado en host"
  additional_tools:
    - "vim (fallback)"
    - "gh CLI (GitHub)"

issues_found:
  - issue: "PAT de GitHub aparece en git remote -v aunque .git/config esta limpio"
    resolved: false
    resolution: "Causa identificada: helper credential-libsecret configurado pero no instalado, falla y cae a otro helper que inyecta el token en la URL resuelta. Decision del humano: continuar sin rotar el token; registrar como ESC-001 abierta en CHECKPOINT_GLOBAL. No bloquea la fase."
  - issue: "npm 10.9.2 detectable desde bash WSL pero proviene del Herd/nvm de Windows (C:\\Users\\aviera\\...\\Herd\\bin\\nvm\\v23.7.0)"
    resolved: true
    resolution: "DEC-012 hace irrelevante este punto: el Node a usar sera el de la imagen Docker node:20-alpine. El npm de Windows queda ignorado."

skills_suggested:
  - skill: "bake/make/just como atajos de docker compose run --rm"
    accepted: "pendiente decidir en fase 02 (Planning) por devops-engineer/software-architect"

deliverables_obligatorios_heredados_a_fases_siguientes:
  - id: "DEL-001"
    titulo: "docs/CONVENCIONES_PLATAFORMA.md"
    descripcion: "Documento versionado con convenciones de puertos, redes Docker, volumenes, naming de contenedores, subdominios y env vars que eviten colisiones entre Maestro y apps huesped"
    fase_objetivo: "02-planning (diseno inicial) + 04-delivery (version final consolidada)"
    origen: "DEC-012"
  - id: "DEL-002"
    titulo: "docker-compose.dev.yml portatil"
    descripcion: "Stack completo del Maestro levantable con `docker compose up -d` sin prerequisitos de runtime en host"
    fase_objetivo: "03-development / 04-delivery"
    origen: "DEC-012"
  - id: "DEL-003"
    titulo: "SETUP_GUIDE.md en docs/"
    descripcion: "Guia de onboarding para nuevos devs con solo Docker + git + IDE"
    fase_objetivo: "04-delivery (via documentation-writer)"
    origen: "regla general + DEC-012"

siguiente_fase: "01-discovery"
handoff_al_PM: |
  Fase 00 completada. Entorno dev funcional verificado con criterios simplificados
  por DEC-012 (zero local installs). Dos issues documentados:
  (a) ESC-001 PAT en git remote, no bloqueante.
  (b) cliente BD grafico en host pendiente de confirmacion del humano, no bloqueante.
  Tres deliverables obligatorios heredados a fases siguientes (DEL-001/002/003).
```
