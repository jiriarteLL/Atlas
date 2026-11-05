# Migración de datos v1 → v2 (DT-10)

`migrar_datos_v1.py` pasa los datos del Inventario v1 (`C:\AssetManager\assetmanager.db`, SQLite) a la base de la v2 que indique `DATABASE_URL` (PostgreSQL en Azure/Dokploy, o SQLite para ensayar).

## Qué pasa

| v1 | v2 |
|---|---|
| assets, asset_glpi, historial, snapshots, tickets, audit_log, proyectos (+ responsables, tareas, activos) | Igual, con las mismas claves. Las columnas nuevas de la v2 (`ip_publica`, `mac`, `user_agent`, etc.) quedan con su valor por defecto. |
| adjuntos (archivo en `C:\AssetManager\adjuntos`) | El contenido del archivo se guarda en la base (ADR-001). |
| users | Mismo usuario, email y contraseña (bcrypt compatible). Rol: admin → admin, editor → editor, cualquier otro → viewer. El usuario genérico `admin` no pasa: la v2 tiene su propio superadmin `admin@llyasoc.com`. |

El texto con el carácter NUL (algunos tickets) se limpia, porque PostgreSQL no lo acepta.

## Garantías

- La base v1 **no se escribe**: el script toma una copia consistente y lee la copia.
- Todo va en **una sola transacción**. Si algo falla o los conteos no cierran, no queda nada a medias.
- **Sin `--confirmar` es un simulacro**: hace todo, verifica y deshace.
- Se niega a correr si el destino ya tiene activos.

## Uso

Con el Python del venv de la v2 (tiene las dependencias):

```powershell
$env:DATABASE_URL = "postgres://USUARIO:CLAVE@HOST:5432/inventario?sslmode=require"
C:\AssetManagerV2\.venv\Scripts\python.exe migrar_datos_v1.py --origen C:\AssetManager\assetmanager.db              # simulacro
C:\AssetManagerV2\.venv\Scripts\python.exe migrar_datos_v1.py --origen C:\AssetManager\assetmanager.db --confirmar  # guarda
```

Opciones: `--adjuntos <carpeta>`, `--omitir-usuarios admin,otro`, `--sin-usuarios`.

## El día del pase

1. Frenar las escrituras en la v1: detener `InventarioLLYA-HTTP` y `InventarioLLYA-SSL` (los agentes reintentan solos en su próxima corrida).
2. Correr el simulacro contra el destino real. Si cierra, correr con `--confirmar`.
3. Levantar la v2 (su arranque corre `seed.py`, que crea el superadmin si no existe).
4. Revisar en la web: cantidad de activos, una ficha con historial, proyectos y tickets.
5. Recién ahí apuntar los agentes a la v2. Si algo sale mal, se vuelve a levantar la v1, que quedó intacta.

## Ensayo hecho (05/11/2026)

Contra la base real de producción, con destino SQLite: 664 activos, 114.302 registros de historial, 789 de auditoría, 63 tickets, 1 proyecto, 1 adjunto y 7 usuarios. Todos los conteos cerraron, en unos 55 segundos. Después se levantó la v2 sobre esa base y respondieron el login, `/api/assets` (664), el historial, los proyectos y los tickets.

**Falta probarlo contra PostgreSQL.** Se hace con el simulacro contra el servidor de Azure apenas exista.
