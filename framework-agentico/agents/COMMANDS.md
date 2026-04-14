# Catálogo de Comandos

> **Versión:** 1.0.0  
> **Convención:** `/nivel:acción` o `/nivel:fase:acción`

---

## Comandos del Project Manager

| Comando | Acción | Modo |
|---------|--------|------|
| `/pm` | Entrada general, conversación con el PM | Interactivo |
| `/pm:orquestar` | Ejecuta el proyecto completo fase por fase | Ejecución |
| `/pm:planificar` | Analiza y planifica sin ejecutar ni editar | Solo lectura |
| `/pm:estado` | Muestra estado actual desde CHECKPOINT_GLOBAL | Consulta |
| `/pm:reporte` | Genera reporte ejecutivo via executive-reporter | Consulta |
| `/pm:fase N` | Activa directamente la fase N (valida prerrequisitos) | Ejecución |

---

## Comandos por Fase

Aplican a todas las fases (00 a 06). Reemplazar `{fase}` por el nombre:
`setup`, `discovery`, `planning`, `development`, `delivery`, `operations`, `retrospective`

| Comando | Acción | Modo |
|---------|--------|------|
| `/fase:{fase}:orquestar` | Ejecuta la fase completa | Ejecución |
| `/fase:{fase}:planificar` | Planifica la fase sin ejecutar | Solo lectura |
| `/fase:{fase}:estado` | Muestra checkpoint de la fase | Consulta |

### Ejemplos

```
/fase:setup:orquestar
/fase:discovery:planificar
/fase:planning:estado
/fase:development:orquestar
/fase:delivery:planificar
/fase:operations:estado
/fase:retrospective:orquestar
```

---

## Comandos Transversales

| Comando | Acción | Modo |
|---------|--------|------|
| `/transversal:orquestar` | Ejecuta ciclo completo de validación transversal | Ejecución |
| `/transversal:planificar` | Analiza sin ejecutar | Solo lectura |
| `/transversal:estado` | Muestra checkpoint transversal | Consulta |
| `/transversal:reporte` | Genera reporte consolidado de todos los transversales | Consulta |

---

## Reglas de Ejecución

```yaml
reglas_generales:
  - todo comando de ejecución (:orquestar) puede editar archivos y ejecutar comandos
  - todo comando de planificación (:planificar) solo analiza y recomienda, nunca edita
  - todo comando de consulta (:estado, :reporte) muestra información sin modificar nada
  - al invocar una fase directamente, el PM valida que las fases anteriores estén completas
  - si las fases anteriores no están completas, el PM pregunta al humano antes de proceder
  - el modo planificar está disponible en todos los niveles independientemente del estado de fases

precedencia:
  - el PM puede invocar cualquier orquestador de fase o transversal
  - los orquestadores de fase pueden solicitar al orquestador transversal
  - los agentes individuales no se invocan directamente; sus orquestadores los coordinan
  - el humano puede invocar cualquier nivel directamente via comandos
```
