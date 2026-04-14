# Documentación Fase 02 — Planning

## Templates de esta fase

### ARCHITECTURE.md

```markdown
# Arquitectura del Sistema

## 1. Visión General
<!-- Descripción de alto nivel de la solución -->

## 2. Stack Tecnológico
<!-- Lenguaje, framework, BD, frontend, ORM, herramientas -->

## 3. Patrón Arquitectónico
<!-- Monolito modular, microservicios, event-driven, hexagonal, etc. -->

## 4. Diagrama de Componentes
<!-- Diagrama C4 nivel 2 mínimo (mermaid o ASCII) -->

## 5. Estrategia de Error Handling
<!-- Retry policies, circuit breakers, fallbacks, error codes -->

## 6. Estrategia de Branching
<!-- Git flow, trunk-based, convención de commits -->

## 7. Estrategia de Ambientes
<!-- Local, dev, staging, producción -->

## 8. Internacionalización
<!-- Estrategia de i18n si aplica -->

## 9. Integración con Plataforma
<!-- Solo si preset activo: detalles de integración -->
```

### ADR_LOG.md

```markdown
# Registro de Architecture Decision Records

## ADR-001: [Título]
- **Estado:** Aceptado | Propuesto | Rechazado
- **Contexto:** [Qué problema resuelve]
- **Decisión:** [Qué se decidió]
- **Alternativas consideradas:** [Qué otras opciones había]
- **Consecuencias:** [Trade-offs, implicaciones]
- **Fecha:** [YYYY-MM-DD]
```

### DATA_MODEL.md

```markdown
# Modelo de Datos

## 1. Diagrama ER
<!-- Diagrama de entidad-relación (mermaid o ASCII) -->

## 2. Entidades Principales
<!-- Descripción de cada entidad, atributos clave, relaciones -->

## 3. Estrategia de Migración
<!-- Herramienta, convenciones de naming, rollback -->

## 4. Índices y Optimización
<!-- Índices planificados, estrategia de particionamiento si aplica -->

## 5. Políticas de Datos
<!-- Retención, backup, aislamiento (multi-tenancy si aplica) -->
```

### API_CONTRACTS.md

```markdown
# Contratos de API

## 1. Convenciones Generales
<!-- Formato de URLs, versionado, paginación, formato de errores -->

## 2. Autenticación
<!-- Mecanismo de auth, headers requeridos -->

## 3. Endpoints

### [Módulo / Recurso]
<!-- Método | Ruta | Descripción | Request body | Response | Códigos de error -->

## 4. Hooks / Webhooks
<!-- Endpoints que reciben eventos externos -->

## 5. Comunicación Inter-Servicios
<!-- Si aplica: gateway, eventos, colas -->
```

### UX_SPECS.md

```markdown
# Especificaciones de UX

## 1. Flujos de Usuario
<!-- Flujos principales mapeados paso a paso -->

## 2. Sistema de Diseño
<!-- Colores, tipografía, espaciado, componentes base -->

## 3. Wireframes
<!-- Descripción de wireframes por pantalla clave -->

## 4. Accesibilidad
<!-- Nivel WCAG objetivo, consideraciones específicas -->

## 5. Responsive
<!-- Breakpoints, adaptaciones por dispositivo -->
```
