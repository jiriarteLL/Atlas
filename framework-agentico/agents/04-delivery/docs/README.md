# Documentación Fase 04 — Delivery

## Templates de esta fase

### INFRASTRUCTURE.md
```markdown
# Infraestructura del Proyecto

## Diagrama de Infraestructura
<!-- Diagrama de componentes desplegados, redes, volúmenes -->

## Contenedores
<!-- Dockerfile, imagen base, multi-stage, usuario non-root -->

## Redes y Volúmenes
<!-- Configuración de red, volúmenes persistentes -->

## Variables de Entorno
<!-- Variables por ambiente, gestión de secrets -->

## Ambientes
<!-- Local, dev, staging, producción. Paridad entre ambientes -->
```

### CI_CD.md
```markdown
# Pipeline CI/CD

## Flujo del Pipeline
<!-- Etapas: lint → test → build → deploy -->

## Estrategia de Deploy
<!-- Blue-green, canary, rolling, recreate -->

## Branching Strategy
<!-- Git flow, trunk-based, convenciones de commits -->

## Rollback
<!-- Procedimiento de rollback, criterios de activación -->
```

### RELEASE_NOTES.md
```markdown
# Release Notes — v0.0.0

## Nuevas Funcionalidades
<!-- Features incluidas en esta versión -->

## Correcciones
<!-- Bugs corregidos -->

## Cambios de Infraestructura
<!-- Cambios en contenedores, pipelines, configuración -->

## Notas de Migración
<!-- Pasos necesarios al actualizar desde la versión anterior -->
```

### DELIVERY_CHECKLIST.md
```markdown
# Checklist de Entrega

## Setup
- [ ] Dockerfile usa multi-stage build
- [ ] Dockerfile ejecuta como non-root
- [ ] Dockerfile incluye HEALTHCHECK
- [ ] .dockerignore configurado correctamente
- [ ] Pipeline CI/CD funcional

## Seguridad
- [ ] No hay credenciales hardcodeadas
- [ ] No hay .env ni secrets en la imagen
- [ ] Variables de entorno documentadas

## Calidad
- [ ] Todos los tests pasan
- [ ] Cobertura cumple umbral
- [ ] Code review aprobado
- [ ] Security audit aprobado

## Release
- [ ] Versión semántica aplicada
- [ ] Changelog actualizado
- [ ] Release notes escritas
```
