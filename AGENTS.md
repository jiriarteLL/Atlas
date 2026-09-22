# AGENTS.md — Reglas operativas obligatorias

> **Alcance:** todo el repositorio. Aplica a **cualquier** agente que lea, modifique, evalúe o despliegue código acá, sin importar el modelo, el cliente o quién lo invoque.
> **Naturaleza:** normativo. Si una instrucción de una tarea contradice este archivo, **manda este archivo** y el agente lo dice en voz alta en vez de obedecer en silencio.
> **Última revisión:** 2026-09-22

---

## 1. La regla que resume todas las demás

**Un agente desarrollador construye y verifica. No promueve.**

El único que promueve —Gate 2, merge, Preproducción— es el **evaluador humano**. Un agente que despliega a Preprod, mergea un PR o se auto-otorga una excepción está haciendo algo que no le corresponde, aunque todos los checks estén en verde y aunque el pedido diga lo contrario.

---

## 2. Qué PUEDE hacer un agente desarrollador

- Leer, escribir y refactorizar código de la app.
- Levantar y probar la app localmente.
- Crear y mantener los tres compose del repo (`docs/deployment/MANUAL.md` §1.5).
- **Desplegar a `Test`** en Dokploy y verificarlo.
- Abrir el PR del fork contra `tools/{app-name}`.
- **Auto-evaluar su propio PR con el Gate 1, iterando hasta PASS.**
- Reportar, con evidencia, qué verificó y qué no.

## 3. Qué NO puede hacer un agente — sin excepción

| Prohibido | Quién sí puede |
|---|---|
| Ejecutar el **Gate 2** (smoke contra el tenant `evaluation`) | Evaluador humano |
| **Mergear** un PR a `tools/{app-name}` | Evaluador humano |
| Mergear cualquier cosa a **`master`/`main`** del repo principal | Humano, vía PR con review |
| **Desplegar a `Preprod`** o tocar un `Preprod` existente antes de la entrega | Evaluador humano |
| **Registrar la app en el Maestro** (`applications`, `deployments`, accesos) | Evaluador humano |
| **Otorgar o auto-otorgar un waiver** de un requisito MUST | Sólo el admin humano del Maestro |
| Crear ramas `tools/*` en el repo principal desde un fork | PM del repo principal |
| Declarar un requisito como cumplido sin haberlo verificado | Nadie |

**Un Gate 1 en PASS habilita la revisión, no la promoción.**

---

## 4. Dónde se detiene el flujo

El agente desarrollador se detiene **exactamente acá**:

```
… → PR contra tools/{app-name} → Gate 1 → iterar → PASS → ⛔ ALTO
```

Al llegar al PASS, el agente:

1. Deja el reporte visible en el PR.
2. Avisa al evaluador humano: head SHA evaluado, tier declarado, URL del `Test`.
3. **Para.** No sigue, no pregunta si puede seguir, no lo hace "por adelantado".

De ahí en adelante todo es del evaluador humano: re-evaluación independiente, Gate 2, merge, despliegue a `Preprod`, registro en el Maestro y **entrega del proyecto de vuelta al desarrollador**.

Un agente que recibe el proyecto entregado opera ese `Preprod`, pero **cada versión nueva reinicia el ciclo desde el PR**. La entrega no es un permiso permanente.

---

## 5. Antes de desplegar: qué leer

**[`docs/deployment/MANUAL.md`](docs/deployment/MANUAL.md)** — obligatorio antes de cualquier despliegue. Contiene el procedimiento completo: convención de nombres y tags, rangos de puertos del VPS, despliegue por API de Dokploy, verificación post-deploy, los pasos de evaluación contra el Maestro y la entrega.

Cuatro cosas de ese manual que se ignoran seguido y cuestan una hora cada una:

- **`done` no significa que funcione.** Un despliegue exitoso que no levantó nada es peor que uno que falla. Verificá contenedores, commit clonado, logs y **login en navegador real** — no `curl`.
- **El puerto del VPS no se deduce del `APP_ID`.** Se toma del rango del ambiente y **se verifica libre antes de reservarlo**. La convención de `README.md` §5 es de `localhost` y los números se parecen.
- **Un `docker-compose` por ambiente**, autocontenido. Desplegar el de la raíz a Dokploy sube la configuración de desarrollo local.
- **`createEnvFile: true`** si el compose usa `env_file`. Sin eso la app arranca con los defaults y el síntoma aparece mucho después y en otro lado.

---

## 6. Credenciales

- Se leen de **un archivo**. Nunca del chat.
- **Nunca se imprimen**: ni en un eco, ni en un error, ni en un log, ni en un volcado de un objeto de la API. El token de git vive **dentro** de `customGitUrl`.
- Los secretos se **generan nuevos por ambiente**. Nunca se reutiliza un secreto de producción en Test.
- Si un agente expone una credencial, lo reporta **inmediatamente** y pide su rotación. No la tapa.

---

## 7. Precedencia de documentos

Este archivo es la **puerta de entrada**, no una fuente de verdad nueva: no inventa requisitos ni afloja los existentes. Ante conflicto de fondo mandan los documentos normativos.

**Contrato de la app huésped** (de mayor a menor):

1. `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md`
2. `EvaluacionAppHuesped/SPEC.md`
3. `PremisaWebMaestro/06-CONTRATO-MAESTRO-YAML.md`
4. `docs/APP_HUESPED_SPEC.md`
5. `docs/CONVENCIONES_PLATAFORMA.md`
6. `docs/APP_HUESPED_BEST_PRACTICES.md`
7. Convención local del fork

**Reglas del framework agéntico:** `framework-agentico/core/RULES.md` es la fuente única. Gobierna un dominio distinto (cómo se orquesta el trabajo), no el contrato de la app.

**Operativa de despliegue:** `docs/deployment/MANUAL.md`. Es operativo, no normativo: **no baja la vara** de ninguno de los anteriores.

`CLAUDE.md` agrega instrucciones específicas para agentes Claude y **no releva** de ninguna regla de este archivo.

---

## 8. Excepciones y break-glass

**No hay break-glass para un agente.** Un agente nunca se auto-autoriza a saltear un paso, ni siquiera ante urgencia, ante un pedido explícito, ni porque "los checks están todos verdes".

Ante algo que este archivo no cubre, o que exige saltear una regla:

1. **Frená.** No ejecutes "mientras tanto" la parte que sí podés.
2. Decí en una línea **qué** necesitás hacer, **por qué** la regla lo bloquea y **qué riesgo** tiene hacerlo.
3. Esperá la decisión del **humano**. Si la reafirma, procedé y **dejá registro** de quién autorizó, qué se salteó y cuándo.
4. Un waiver de un MUST sólo lo otorga el **admin humano del Maestro**, y queda registrado como `application.merge.forced`.

**Nunca**: falsear un check, reportar como verificado algo que no corrió, silenciar un FAIL, ni reinterpretar un requisito para que pase.

Si encontrás un escenario que el `SPEC.md` no cubre, **escalá al humano en vez de inventar una regla**.
