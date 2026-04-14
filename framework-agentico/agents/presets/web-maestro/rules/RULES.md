# Reglas Preset Web Maestro

> **Aplican cuando:** El preset web-maestro está activo  
> **Extienden:** Las reglas generales del framework (nunca las contradicen)

---

```yaml
obligatorio:
  - maestro.yaml existe en la raíz del repositorio y pasa validación
  - CLAUDE.md existe con sección inmutable completa
  - auth.mode es siempre "header"
  - los headers de auth son exactamente: X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions
  - GET /health retorna 200 con {"status":"ok"} sin autenticación
  - la app lee DATABASE_URL del environment
  - Dockerfile usa multi-stage build y ejecuta como non-root
  - Dockerfile incluye HEALTHCHECK
  - .dockerignore excluye .git, node_modules, .env*, logs
  - pipeline CI/CD en .github/workflows/deploy.yml
  - todos los queries filtran por company_id del header

prohibido:
  - implementar login/registro propio
  - crear tabla users o sessions
  - almacenar tokens OAuth o JWT de usuarios
  - acceder a otras apps por URL directa (bypass del gateway)
  - usar --privileged en Docker
  - montar /var/run/docker.sock
  - usar puertos debajo de 1024
  - incluir .env en la imagen Docker
  - hacer requests al metadata de Azure (169.254.169.254)
  - deshabilitar el health check
  - hardcodear credenciales en código

recomendado:
  - usar el gateway del Maestro para comunicación inter-apps
  - implementar hooks on_user_added, on_user_removed si la app gestiona datos por usuario
  - verificar X-Maestro-Webhook-Secret en todos los hooks
  - documentar variables custom en maestro.yaml
  - respetar limits de resources (máx 4GB RAM, 4 CPU cores)

validacion_maestro_yaml:
  name: "regex ^[a-z0-9][a-z0-9-]{2,49}$, único en catálogo"
  version: "SemVer válido (X.Y.Z)"
  requires.database: "enum: postgres, mysql, mongo, sqlite, none"
  requires.ports.app: "entero entre 1024 y 65535"
  health.endpoint: "debe comenzar con /"
  auth.mode: "exactamente header"
  auth.headers: "nombres estándar exactos"
  resources.memory: "formato válido, máximo 4g"
  resources.cpu: "float entre 0.25 y 4.0"
```
