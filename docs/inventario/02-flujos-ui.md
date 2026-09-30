# Inventario LLYA v2 — Flujos de usuario (fase 02-planning)

## Sesión

1. **Entrada:** el Maestro abre la URL de la app en `target="_blank"`, o el usuario entra directo (modo standalone).
2. **Recuperar la sesión:** al cargar, el frontend llama a `POST /auth/refresh`. Si la cookie `inventario_session`
   sigue vigente, entra sin pedir la contraseña; si no, muestra el login.
3. **Login:** usuario o email más contraseña. Si hay error, el mensaje es siempre el mismo. Si hay demasiados
   intentos, se informa que hay que esperar.
4. **Cambio obligatorio:** si `debe_cambiar_password` (superadmin recién sembrado o contraseña reseteada por un
   admin), aparece una pantalla que no deja seguir hasta cambiarla. Después del cambio hay que volver a entrar.
5. **Renovación:** el access token se renueva solo, al 80 % de su vida (unos 12 minutos). Si la renovación falla,
   la app vuelve al login.
6. **Logout:** "Cerrar sesión" revoca el access y el refresh en el servidor.

## Activos

- **Dashboard:** métricas (total, en mantenimiento, garantías por vencer, notebooks asignadas / sin asignar,
  impresoras, servidores), gráficos por sede, tipo y antigüedad del último reporte, y los últimos sincronizados.
  Cada tarjeta o barra lleva al listado ya filtrado.
- **Listado:** búsqueda y filtros por tipo, estado, sede y alertas (sin reportar hace más de 30 días, garantía por
  vencer, sin EDR, discos sin cifrar, AnyDesk, batería por debajo del 70 %). Se puede ordenar, pagina de a 50 y
  exporta a Excel.
- **Ficha:** identificación con QR; hardware; seguridad (cifrado, TPM, datos GLPI); asignación; impresoras;
  software; adjuntos; historial. Con permiso: editar, eliminar y consultar la garantía Lenovo.
- **Nuevo activo, importar/exportar CSV:** solo con `inventario.editar`.

## Proyectos

Listado con estado y avance. En la ficha del proyecto se asignan responsables (usuarios de la app), se vinculan
activos y se gestionan tareas (Pendiente → En proceso → Realizado). Al pasar el proyecto a Finalizado se avisa por
mail a los responsables y al creador.

## Reportes y Tendencias

Gráficos por sede, tipo y estado, exportables a Excel con la imagen del gráfico. En Tendencias se ve la evolución
de cada métrica entre snapshots.

## Administración

- **Configuración** (solo `usuarios.administrar`): alta de usuarios (usuario, email, nombre, contraseña, rol),
  cambio de rol, reset de contraseña y baja. El superadmin no se puede degradar ni dar de baja.
- **Mi perfil:** datos propios, permisos, actividad reciente y cambio de contraseña.
- **Agente:** instrucciones para instalar los agentes, con la URL del ambiente actual.
