# Reglas Fase 04 — Delivery

```yaml
reglas:
  - todo Dockerfile debe usar multi-stage build
  - todo contenedor debe ejecutar como usuario non-root
  - todo Dockerfile debe incluir HEALTHCHECK
  - .dockerignore debe excluir .git, node_modules, .env*, logs, tests
  - nunca incluir secrets ni .env en la imagen Docker
  - pipeline CI/CD debe ejecutar tests antes de build
  - pipeline CI/CD debe ejecutar linting antes de tests
  - versionado semántico estricto (MAJOR.MINOR.PATCH)
  - toda release tiene changelog y release notes
  - el sistema debe compilar y arrancar antes de marcar la fase como completa
  - smoke tests son obligatorios post-ensamblaje

ambientes:
  - definir al menos: local (docker-compose.dev.yml) y producción
  - garantizar paridad máxima entre ambientes
  - variables de entorno diferenciadas por ambiente
  - nunca credenciales de producción en ambientes de desarrollo

si_preset_web_maestro:
  - maestro.yaml debe pasar validación contra schema del contrato
  - Dockerfile no debe usar --privileged ni montar docker.sock
  - no usar puertos debajo de 1024
  - pipeline CI/CD en .github/workflows/deploy.yml
  - rama main protegida, todo via PR con review
  - verificar checklist completo de sección 19 del contrato
```
