# -*- coding: utf-8 -*-
"""Migracion + seeder idempotente del superadmin (README §10, fase 05-seeding).

Uso: python seed.py   (el entrypoint del contenedor lo corre antes de levantar la app)
- Crea las tablas que falten y completa roles/permisos.
- Crea admin@llyasoc.com con rol superadmin si no existe, con SUPERADMIN_INITIAL_PASSWORD.
- Si ya existe, NO toca su password; solo le asegura el rol superadmin.
- Falla (exit != 0) si la password falta o es debil.
"""
import os
import sys

import config
from database import SessionLocal, init_db
from auth import User, UserRole, asignar_rol, hash_password, sincronizar_roles, validar_password


class SeedError(Exception):
    pass


def seed_superadmin():
    password = os.getenv("SUPERADMIN_INITIAL_PASSWORD", "")
    if not password:
        raise SeedError("SUPERADMIN_INITIAL_PASSWORD no esta definida")
    motivo = validar_password(password)
    if motivo:
        raise SeedError("SUPERADMIN_INITIAL_PASSWORD rechazada: " + motivo)

    init_db()
    db = SessionLocal()
    try:
        roles = sincronizar_roles(db)
        email = config.SUPERADMIN_EMAIL
        u = db.query(User).filter(User.username == email).first()
        if not u:
            u = User(username=email, email=email, nombre="Super Admin", activo="1",
                     password_hash=hash_password(password), debe_cambiar_password=True)
            db.add(u)
            db.flush()
            asignar_rol(db, u, "superadmin")
            estado = "creado"
        else:
            tiene = db.query(UserRole).filter(UserRole.user_id == u.id,
                                              UserRole.role_id == roles["superadmin"].id).first()
            if not tiene:
                asignar_rol(db, u, "superadmin")
                estado = "existia, se le asigno el rol superadmin"
            else:
                estado = "ya existia, password sin cambios"
        db.commit()
        return estado
    finally:
        db.close()


def seed_licencias():
    """Catalogo de licencias contratadas (sin costos ni personas). Idempotente: no duplica ni pisa lo existente."""
    import licencias
    db = SessionLocal()
    try:
        creados = licencias.sembrar_catalogo(db)
        db.commit()
        return creados
    finally:
        db.close()


def main():
    try:
        estado = seed_superadmin()
    except SeedError as e:
        print("[seed] ERROR: %s" % e, file=sys.stderr)
        return 1
    print("[seed] superadmin %s: %s" % (config.SUPERADMIN_EMAIL, estado))
    creados = seed_licencias()
    print("[seed] licencias: %s" % ("catalogo creado: " + ", ".join(creados) if creados else "catalogo ya cargado"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
