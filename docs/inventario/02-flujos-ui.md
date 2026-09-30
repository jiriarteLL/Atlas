# Inventario LLYA v2 — Flujos de usuario (fase 02-planning)

## Sesión

1. **Entrada:** el Maestro abre la URL de la app en `target="_blank"`, o el usuario entra directo (modo standalone).
2. **Intro:** la primera vez en la pestaña se ve la secuencia de arranque (contador con el último total de activos
   visto en ese navegador, sin datos del servidor) y el botón ENTRAR. Enter también entra.
3. **Recuperar la sesión:** al cargar, el frontend llama a `POST /auth/refresh`. Si la cookie `inventario_session`
   sigue vigente, entra sin pedir la contraseña; si no, muestra el login.
4. **Login:** usuario o email más contraseña. Si hay error, el mensaje es siempre el mismo. Si hay demasiados
   intentos, se informa que hay que esperar.
5. **Cambio obligatorio:** si `debe_cambiar_password` (superadmin recién sembrado o contraseña reseteada por un
   admin), aparece una pantalla que no deja seguir hasta cambiarla. Después del cambio hay que volver a entrar.
6. **Renovación:** el access token se renueva solo, al 80 % de su vida (unos 12 minutos). Si la renovación falla,
   la app vuelve al login.
7. **Logout:** "Cerrar sesión" revoca el access y el refresh en el servidor.

## Activos

- **Dashboard:** ocho tarjetas (total, en mantenimiento, garantías por vencer, notebooks total / asignadas / sin
  asignar, impresoras, servidores; licencias Claude y asignadas se muestran con "—" porque el módulo no está en
  esta versión), barras por sede, dona por tipo y los últimos sincronizados. Cada tarjeta o barra lleva al
  listado ya filtrado.
- **Listado:** búsqueda y filtros por tipo, estado, sede y alertas (sin reportar hace más de 30 días, garantía por
  vencer, sin EDR, discos sin cifrar, AnyDesk, batería por debajo del 70 %). Se puede ordenar, pagina de a 50 y
  exporta a Excel.
- **Ficha** (panel lateral): estado y último sync; QR; hardware; seguridad (cifrado, TPM, datos GLPI); asignación; impresoras;
  software; licencias vinculadas (diseño, sin datos); adjuntos; historial. Con permiso: editar, eliminar y consultar la garantía Lenovo.
- **Nuevo activo, importar/exportar CSV:** solo con `inventario.editar`.

## Proyectos

Listado con estado y avance. En la ficha del proyecto se asignan responsables (usuarios de la app), se vinculan
activos y se gestionan tareas (Pendiente → En proceso → Realizado). Al pasar el proyecto a Finalizado se avisa por
mail a los responsables y al creador.

## Reportes y Tendencias

Cuatro indicadores (tasa operativa, en mantenimiento, sedes con inventario, licencias por vencer) y gráficos
por sede, tipo, estado y equipos sin reportar, exportables a Excel con la imagen del gráfico. En Tendencias se ve la evolución
de cada métrica entre snapshots.

## Administración

- **Licencias y Usuarios (nómina):** pantallas del diseño sin datos, con el aviso "Módulo no incluido en esta
  versión" (ADR-003, DT-09).
- **Accesos** (Herramientas, solo `usuarios.administrar`): tarjetas con los usuarios de la app; alta de usuarios (usuario, email, nombre, contraseña, rol),
  cambio de rol, reset de contraseña y baja. El superadmin no se puede degradar ni dar de baja.
- **Mi perfil:** datos propios, permisos, actividad reciente y cambio de contraseña.
- **Agente:** instrucciones para instalar los agentes, con la URL del ambiente actual.
- **Configuración → Ambientación:** color de acento (Cian, Violeta, Esmeralda, Ámbar), fondo animado, intensidad
  de brillo y ambiente sonoro. Se guarda solo en ese navegador; si no hay almacenamiento, usa los valores por
  defecto. Con "reducir movimiento" del sistema no hay animaciones.
