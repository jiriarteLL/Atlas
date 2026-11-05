# -*- coding: utf-8 -*-
"""Migra los datos del Inventario v1 (SQLite, C:\\AssetManager) a la v2 (DT-10 / issue 16).

El destino es la base que indique DATABASE_URL: PostgreSQL (Azure, Dokploy) o SQLite (ensayo local).
Usa los modelos de la v2, asi que el esquema destino es exactamente el de la app (Alembic incluido).

Uso:
    set DATABASE_URL=postgres://usuario:clave@host:5432/inventario?sslmode=require
    python migrar_datos_v1.py --origen C:\\AssetManager\\assetmanager.db               (simulacro: no guarda)
    python migrar_datos_v1.py --origen C:\\AssetManager\\assetmanager.db --confirmar   (guarda)

Garantias:
- La base v1 nunca se escribe: se toma una copia consistente (API de backup de SQLite) y se lee la copia.
- Todo va en UNA transaccion: si algo falla o los conteos no cierran, no queda nada a medias.
- Sin --confirmar hace todo y al final deshace (sirve para ensayar contra la base real de destino).
- Se niega a correr si el destino ya tiene activos (no mezcla datos).
- Los usuarios conservan su password (bcrypt de la v1, compatible) y su rol (admin / editor / viewer).
"""
import argparse
import os
import secrets
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime

# La v2 exige JWT_SECRET al importar config; el script no emite tokens, asi que alcanza uno descartable.
os.environ.setdefault("JWT_SECRET", secrets.token_hex(32))

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app", "backend"))
sys.path.insert(0, BACKEND)

from sqlalchemy import DateTime, Integer, String, Text, func, select  # noqa: E402

# Tablas de negocio que pasan tal cual (columnas en comun; las nuevas de la v2 toman su default).
TABLAS = ["assets", "asset_glpi", "historial", "snapshots", "tickets", "audit_log",
          "proyectos", "proyecto_responsables", "proyecto_tareas", "proyecto_activos"]
LOTE = 2000
ROLES_V1 = {"admin": "admin", "editor": "editor"}  # cualquier otro rol de la v1 pasa como viewer


def log(msg):
    print(msg, flush=True)


def copiar_origen(ruta):
    """Copia consistente de la base v1 a un temporal; devuelve (conexion, carpeta temporal)."""
    if not os.path.isfile(ruta):
        sys.exit("No existe la base de origen: %s" % ruta)
    tmp = tempfile.mkdtemp(prefix="migrar_v1_")
    copia = os.path.join(tmp, "v1.db")
    src = sqlite3.connect("file:%s?mode=ro" % ruta.replace("\\", "/"), uri=True, timeout=30)
    dst = sqlite3.connect(copia)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    con = sqlite3.connect(copia)
    con.row_factory = sqlite3.Row
    return con, tmp


def a_fecha(v):
    if v is None or isinstance(v, datetime):
        return v
    v = str(v).strip()
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("T", " ").replace("Z", ""))
    except ValueError:
        return None


def convertir(col, v):
    """Adapta un valor de la v1 al tipo de la columna v2. Los nulos de texto toman el default de la v2."""
    t = col.type
    if isinstance(t, DateTime):
        return a_fecha(v)
    if isinstance(t, Integer):
        if v is None or v == "":
            return None if col.nullable else (col.default.arg if col.default is not None else 0)
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    if isinstance(t, (String, Text)):
        if v is None:
            d = col.default.arg if col.default is not None and not callable(col.default.arg) else None
            return d
        # PostgreSQL no acepta el caracter NUL en texto (SQLite si: hay tickets de la v1 que lo traen).
        return str(v).replace("\x00", "")
    return v


def filas_v1(con, tabla):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)).fetchone():
        return [], []
    cur = con.execute('SELECT * FROM "%s"' % tabla)
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def migrar_tabla(db, tabla_v2, con):
    cols_v1, filas = filas_v1(con, tabla_v2.name)
    comunes = [c for c in tabla_v2.columns if c.name in cols_v1]
    ignoradas = sorted(set(cols_v1) - {c.name for c in comunes})
    if ignoradas:
        log("    columnas de la v1 sin lugar en la v2 (no se pasan): %s" % ", ".join(ignoradas))
    lote = []
    for f in filas:
        lote.append({c.name: convertir(c, f[c.name]) for c in comunes})
        if len(lote) >= LOTE:
            db.execute(tabla_v2.insert(), lote)
            lote = []
    if lote:
        db.execute(tabla_v2.insert(), lote)
    return len(filas)


def ruta_adjunto(archivo, asset_id, carpeta):
    """La v1 guarda rutas absolutas mezclando / y \\; si no esta ahi, se busca en --adjuntos/<asset>/<archivo>."""
    if archivo:
        r = os.path.normpath(archivo.replace("/", os.sep).replace("\\", os.sep))
        if os.path.isfile(r):
            return r
        alt = os.path.join(carpeta, asset_id or "", os.path.basename(r))
        if os.path.isfile(alt):
            return alt
    return None


def migrar_adjuntos(db, tabla, con, carpeta):
    _, filas = filas_v1(con, "adjuntos")
    pasados, faltan = 0, []
    for f in filas:
        r = ruta_adjunto(f["archivo"], f["asset_id"], carpeta)
        if not r:
            faltan.append("%s (%s)" % (f["nombre"], f["archivo"]))
            continue
        with open(r, "rb") as fh:
            contenido = fh.read()
        db.execute(tabla.insert(), [{
            "id": f["id"], "asset_id": f["asset_id"], "nombre": f["nombre"] or "",
            "contenido": contenido, "tipo": f["tipo"] or "", "tamano": len(contenido),
            "descripcion": f["descripcion"] or "", "subido_por": f["subido_por"] or "",
            "fecha": a_fecha(f["fecha"]), "activo": f["activo"] if f["activo"] is not None else "1",
        }])
        pasados += 1
    return len(filas), pasados, faltan


def migrar_usuarios(db, con, omitir):
    from auth import Role, User, UserRole
    roles = {r.nombre: r.id for r in db.query(Role).all()}
    _, filas = filas_v1(con, "users")
    hechos, salteados = [], []
    for f in filas:
        username = (f["username"] or "").strip()
        email = (f["email"] or "").strip().lower() if "email" in f.keys() else ""
        if not username or username in omitir:
            salteados.append("%s (omitido por --omitir-usuarios)" % username)
            continue
        existe = db.query(User).filter(User.username == username).first()
        if not existe and email:
            existe = db.query(User).filter(User.email == email).first()
        if existe:
            salteados.append("%s (ya existe en la v2)" % username)
            continue
        db.add(User(id=f["id"], username=username, email=email or None, password_hash=f["password"],
                    nombre=f["nombre"] or "", activo=str(f["activo"] if f["activo"] is not None else "1"),
                    created=a_fecha(f["created"]), debe_cambiar_password=False))
        db.flush()
        rol = ROLES_V1.get((f["rol"] or "").strip().lower(), "viewer")
        db.add(UserRole(user_id=f["id"], role_id=roles[rol]))
        hechos.append("%s -> %s" % (username, rol))
    db.flush()
    return hechos, salteados


def main():
    ap = argparse.ArgumentParser(description="Migra los datos del Inventario v1 (SQLite) a la v2 (DATABASE_URL).")
    ap.add_argument("--origen", required=True, help="assetmanager.db de la v1 (no se modifica)")
    ap.add_argument("--adjuntos", default=r"C:\AssetManager\adjuntos", help="carpeta de adjuntos de la v1")
    ap.add_argument("--omitir-usuarios", default="admin",
                    help="usuarios de la v1 que no se pasan, separados por coma (default: admin, el generico; "
                         "la v2 tiene su propio superadmin)")
    ap.add_argument("--sin-usuarios", action="store_true", help="no pasar usuarios")
    ap.add_argument("--confirmar", action="store_true", help="guardar los cambios (sin esto es un simulacro)")
    args = ap.parse_args()

    if not os.getenv("DATABASE_URL"):
        sys.exit("Falta DATABASE_URL (la base v2 de destino).")

    import config
    from database import Base, SessionLocal, engine, init_db
    from auth import User, sincronizar_roles

    destino = engine.url.render_as_string(hide_password=True)
    log("Destino: %s" % destino)
    log("Modo: %s" % ("CONFIRMADO (guarda)" if args.confirmar else "SIMULACRO (deshace al final)"))

    log("1/5 Esquema v2 (Alembic)...")
    init_db()

    con, tmp = copiar_origen(args.origen)
    log("2/5 Copia consistente de la v1 tomada: %s" % args.origen)

    tablas = Base.metadata.tables
    db = SessionLocal()
    ok = False
    try:
        sincronizar_roles(db)
        db.flush()
        if db.execute(select(func.count()).select_from(tablas["assets"])).scalar():
            sys.exit("El destino ya tiene activos: la migracion es solo sobre una v2 vacia. No se toco nada.")

        log("3/5 Copiando tablas...")
        esperado = {}
        for nombre in TABLAS:
            n = migrar_tabla(db, tablas[nombre], con)
            esperado[nombre] = n
            log("    %-22s %7d filas" % (nombre, n))
        total_adj, pasados_adj, faltan_adj = migrar_adjuntos(db, tablas["adjuntos"], con, args.adjuntos)
        esperado["adjuntos"] = pasados_adj
        log("    %-22s %7d de %d (archivo leido y guardado en la base)" % ("adjuntos", pasados_adj, total_adj))
        for x in faltan_adj:
            log("    ! adjunto sin archivo, no se pasa: %s" % x)

        if args.sin_usuarios:
            hechos, salteados = [], ["(todos, por --sin-usuarios)"]
        else:
            omitir = {u.strip() for u in args.omitir_usuarios.split(",") if u.strip()}
            hechos, salteados = migrar_usuarios(db, con, omitir)
        log("4/5 Usuarios: %d pasados, %d salteados" % (len(hechos), len(salteados)))
        for x in hechos:
            log("    + %s" % x)
        for x in salteados:
            log("    - %s" % x)

        if engine.dialect.name == "postgresql":
            # audit_log conserva sus ids: la secuencia tiene que seguir desde el maximo.
            from sqlalchemy import text
            db.execute(text("SELECT setval(pg_get_serial_sequence('audit_log','id'), "
                            "COALESCE((SELECT MAX(id) FROM audit_log), 0) + 1, false)"))

        log("5/5 Verificando conteos en el destino...")
        errores = []
        for nombre, n in esperado.items():
            real = db.execute(select(func.count()).select_from(tablas[nombre])).scalar()
            marca = "ok" if real == n else "DIFERENCIA"
            if real != n:
                errores.append(nombre)
            log("    %-22s v1=%-7d v2=%-7d %s" % (nombre, n, real, marca))
        ids_v1 = {r[0] for r in con.execute("SELECT id FROM assets")}
        ids_v2 = {r[0] for r in db.execute(select(tablas["assets"].c.id))}
        if ids_v1 != ids_v2:
            errores.append("assets (ids)")
            log("    assets: los ids no coinciden (%d faltan en la v2)" % len(ids_v1 - ids_v2))
        if errores:
            raise RuntimeError("Los conteos no cierran: %s" % ", ".join(errores))

        if args.confirmar:
            db.commit()
            log("LISTO: migracion guardada.")
        else:
            db.rollback()
            log("SIMULACRO OK: todo cierra. No se guardo nada (correr con --confirmar para guardar).")
        ok = True
    except SystemExit:
        db.rollback()
        raise
    except Exception as e:  # noqa: BLE001
        db.rollback()
        log("ERROR: %s" % e)
        log("Se deshizo todo; el destino quedo como estaba.")
    finally:
        db.close()
        con.close()
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
