# -*- coding: utf-8 -*-
"""Login propio de la app (README §8): users + roles + permissions, JWT con revocacion en logout."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, String, func

import config
from audit import log_action
from database import Base, SessionLocal
from ratelimit import limiter

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=config.BCRYPT_COST)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
auth_router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------- modelos
class User(Base):
    __tablename__ = "users"
    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username       = Column(String, unique=True, nullable=False)
    email          = Column(String, default="")
    password_hash  = Column(String, nullable=False)
    nombre         = Column(String, default="")
    activo         = Column(String, default="1")
    created        = Column(DateTime, default=datetime.utcnow)
    last_login_at  = Column(DateTime, nullable=True)
    # Tokens emitidos antes de esta fecha dejan de valer (cambio de password, desactivacion).
    sesiones_desde = Column(DateTime, nullable=True)


class Role(Base):
    __tablename__ = "roles"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre      = Column(String, unique=True, nullable=False)
    descripcion = Column(String, default="")


class Permission(Base):
    __tablename__ = "permissions"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo      = Column(String, unique=True, nullable=False)
    descripcion = Column(String, default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id       = Column(String, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti     = Column(String, primary_key=True)
    expira  = Column(DateTime, nullable=False)


# ---------------------------------------------------------------- catalogo de roles y permisos
PERMISOS = {
    "inventario.ver":       "Ver inventario, proyectos, reportes y tendencias",
    "inventario.editar":    "Crear y editar activos, proyectos, tareas, tickets y adjuntos",
    "activos.eliminar":     "Eliminar activos",
    "garantias.consultar":  "Consultar garantias en el portal del fabricante",
    "usuarios.administrar": "Administrar usuarios y roles",
}
ROLES = {
    "superadmin": ("Acceso total", list(PERMISOS)),
    "admin":      ("Administrador", list(PERMISOS)),
    "editor":     ("Edita inventario y proyectos", ["inventario.ver", "inventario.editar", "garantias.consultar"]),
    "viewer":     ("Solo lectura", ["inventario.ver"]),
}
# Roles que se pueden asignar desde la API. superadmin solo lo asigna el seeder.
ROLES_ASIGNABLES = ("admin", "editor", "viewer")


def sincronizar_roles(db):
    """Crea o completa roles, permisos y sus pivots. Idempotente: no borra nada que ya exista."""
    perms = {p.codigo: p for p in db.query(Permission).all()}
    for codigo, desc in PERMISOS.items():
        if codigo not in perms:
            perms[codigo] = Permission(codigo=codigo, descripcion=desc)
            db.add(perms[codigo])
    roles = {r.nombre: r for r in db.query(Role).all()}
    for nombre, (desc, _) in ROLES.items():
        if nombre not in roles:
            roles[nombre] = Role(nombre=nombre, descripcion=desc)
            db.add(roles[nombre])
    db.flush()
    existentes = {(rp.role_id, rp.permission_id) for rp in db.query(RolePermission).all()}
    for nombre, (_, codigos) in ROLES.items():
        for codigo in codigos:
            par = (roles[nombre].id, perms[codigo].id)
            if par not in existentes:
                db.add(RolePermission(role_id=par[0], permission_id=par[1]))
    db.flush()
    return roles


def rol_de(db, user_id):
    r = (db.query(Role.nombre).join(UserRole, UserRole.role_id == Role.id)
         .filter(UserRole.user_id == user_id).first())
    return r[0] if r else "viewer"


def permisos_de(db, user_id):
    filas = (db.query(Permission.codigo)
             .join(RolePermission, RolePermission.permission_id == Permission.id)
             .join(UserRole, UserRole.role_id == RolePermission.role_id)
             .filter(UserRole.user_id == user_id).distinct().all())
    return sorted(f[0] for f in filas)


def asignar_rol(db, user, nombre_rol):
    """Deja al usuario con un unico rol."""
    rol = db.query(Role).filter(Role.nombre == nombre_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol invalido.")
    db.query(UserRole).filter(UserRole.user_id == user.id).delete()
    db.add(UserRole(user_id=user.id, role_id=rol.id))


# ---------------------------------------------------------------- passwords
_BLACKLIST = {"admin", "password", "123456789012", "contrasena", "contraseña", "qwertyuiop", "llyasoc",
              "administrador", "password1234", "admin1234567", "passw0rd", "cambiar"}


def validar_password(p):
    """Devuelve None si la password es aceptable, o el motivo del rechazo."""
    p = p or ""
    if len(p) < 12:
        return "La contrasena debe tener al menos 12 caracteres."
    if p.lower() in _BLACKLIST or any(p.lower().startswith(b) and len(set(p.lower()[len(b):])) <= 1 for b in _BLACKLIST):
        return "La contrasena es demasiado comun."
    clases = sum(bool(re.search(x, p)) for x in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    if clases < 3:
        return "La contrasena debe combinar al menos 3 de: minusculas, mayusculas, numeros y simbolos."
    if len(set(p)) < 5:
        return "La contrasena repite demasiado los mismos caracteres."
    return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- schemas
class UserOut(BaseModel):
    username: str
    nombre: str
    rol: str
    email: str = ""
    permisos: List[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    nombre: str
    email: str = ""
    rol: str = "viewer"


class UserUpdate(BaseModel):
    nombre:   Optional[str] = None
    email:    Optional[str] = None
    rol:      Optional[str] = None
    activo:   Optional[str] = None
    password: Optional[str] = None


class ChangePassword(BaseModel):
    password_actual: str
    password_nuevo: str


# ---------------------------------------------------------------- tokens y dependencias
def _ip(request):
    return request.client.host if (request is not None and request.client) else ""


def create_token(username: str) -> str:
    ahora = datetime.now(timezone.utc)
    # "ms": emision en milisegundos, para comparar contra sesiones_desde sin perder precision.
    payload = {"sub": username, "jti": str(uuid.uuid4()), "iat": int(ahora.timestamp()),
               "ms": int(ahora.timestamp() * 1000), "exp": ahora + timedelta(minutes=config.JWT_EXPIRE_MINUTES)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _decodificar(token):
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado.")


def _user_out(db, u):
    return UserOut(username=u.username, nombre=u.nombre or "", email=u.email or "",
                   rol=rol_de(db, u.id), permisos=permisos_de(db, u.id))


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    payload = _decodificar(token)
    no_valido = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado.")
    db = SessionLocal()
    try:
        if not payload.get("jti") or db.get(RevokedToken, payload["jti"]):
            raise no_valido
        u = db.query(User).filter(User.username == payload.get("sub"), User.activo == "1").first()
        if not u:
            raise no_valido
        if u.sesiones_desde and payload.get("ms", 0) <= int(u.sesiones_desde.replace(tzinfo=timezone.utc).timestamp() * 1000):
            raise no_valido
        return _user_out(db, u)
    finally:
        db.close()


def require_permiso(codigo):
    def dep(user: UserOut = Depends(get_current_user)) -> UserOut:
        if codigo not in user.permisos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenes permiso para esta accion.")
        return user
    return dep


require_lectura = require_permiso("inventario.ver")
require_escritura = require_permiso("inventario.editar")
require_admin = require_permiso("usuarios.administrar")


# ---------------------------------------------------------------- endpoints
@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit(config.LOGIN_RATE_LIMIT)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip = _ip(request)
    ident = (form_data.username or "").strip()
    db = SessionLocal()
    try:
        u = (db.query(User).filter(User.activo == "1")
             .filter((User.username == ident) | (func.lower(User.email) == ident.lower())).first())
        if not u or not verify_password(form_data.password, u.password_hash):
            log_action(usuario=ident, accion="LOGIN_FAILED", ip=ip, resultado="failure")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contrasena incorrectos.")
        u.last_login_at = datetime.utcnow()
        db.commit()
        out = _user_out(db, u)
    finally:
        db.close()
    log_action(usuario=out.username, accion="LOGIN_SUCCESS", ip=ip, resultado="success")
    return TokenResponse(access_token=create_token(out.username), expires_in=config.JWT_EXPIRE_MINUTES * 60, user=out)


@auth_router.post("/logout")
def logout(request: Request, token: str = Depends(oauth2_scheme), user: UserOut = Depends(get_current_user)):
    payload = _decodificar(token)
    db = SessionLocal()
    try:
        db.query(RevokedToken).filter(RevokedToken.expira < datetime.utcnow()).delete()
        db.add(RevokedToken(jti=payload["jti"], expira=datetime.utcfromtimestamp(payload["exp"])))
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="LOGOUT", ip=_ip(request))
    return {"status": "ok"}


@auth_router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    return user


@auth_router.get("/perfil")
def perfil(user: UserOut = Depends(get_current_user)):
    from database import AuditLog
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == user.username).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        ultimos = [{"fecha": str(a.timestamp)[:19], "accion": a.accion, "entidad": a.entidad or "", "ip": a.ip_origen or ""}
                   for a in (db.query(AuditLog).filter(AuditLog.usuario == user.username)
                             .order_by(AuditLog.timestamp.desc()).limit(8).all())]
        return {"username": u.username, "nombre": u.nombre or "", "email": u.email or "",
                "rol": user.rol, "activo": u.activo, "creado": str(u.created or "")[:19],
                "permisos": [PERMISOS.get(p, p) for p in user.permisos], "actividad": ultimos}
    finally:
        db.close()


@auth_router.put("/perfil")
def editar_perfil(data: UserUpdate, user: UserOut = Depends(get_current_user)):
    """Cada usuario puede editar su propio nombre y email. Rol y estado no."""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == user.username).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if data.nombre is not None and data.nombre.strip():
            u.nombre = data.nombre.strip()
        if data.email is not None:
            u.email = data.email.strip()
        db.commit()
        return {"username": u.username, "nombre": u.nombre, "email": u.email or "", "rol": user.rol}
    finally:
        db.close()


@auth_router.post("/usuarios")
def crear_usuario(data: UserCreate, request: Request, user: UserOut = Depends(require_admin)):
    if data.rol not in ROLES_ASIGNABLES:
        raise HTTPException(status_code=400, detail="Rol invalido.")
    motivo = validar_password(data.password)
    if motivo:
        raise HTTPException(status_code=400, detail=motivo)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == data.username.strip()).first():
            raise HTTPException(status_code=400, detail="El usuario ya existe.")
        nuevo = User(username=data.username.strip(), password_hash=hash_password(data.password),
                     nombre=data.nombre, email=data.email.strip())
        db.add(nuevo)
        db.flush()
        asignar_rol(db, nuevo, data.rol)
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="CREATE_USER", entidad="usuario", entidad_id=data.username,
               detalle={"rol": data.rol}, ip=_ip(request))
    return {"status": "ok", "username": data.username}


@auth_router.get("/usuarios")
def listar_usuarios(user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    try:
        return [{"username": u.username, "nombre": u.nombre, "email": u.email or "",
                 "rol": rol_de(db, u.id), "activo": u.activo} for u in db.query(User).all()]
    finally:
        db.close()


def _es_superadmin(u):
    return u.username == config.SUPERADMIN_EMAIL


@auth_router.put("/usuarios/{username}")
def editar_usuario(username: str, data: UserUpdate, request: Request, user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        detalle = {}
        if data.rol is not None:
            if data.rol not in ROLES_ASIGNABLES:
                raise HTTPException(status_code=400, detail="Rol invalido.")
            if _es_superadmin(u):
                raise HTTPException(status_code=400, detail="El rol del superadmin no se puede cambiar.")
            if u.username == user.username and data.rol != "admin":
                raise HTTPException(status_code=400, detail="No podes quitarte a vos mismo el rol admin.")
            antes = rol_de(db, u.id)
            if antes != data.rol:
                asignar_rol(db, u, data.rol)
                detalle["rol"] = {"antes": antes, "despues": data.rol}
        if data.nombre is not None and data.nombre.strip():
            u.nombre = data.nombre.strip()
        if data.email is not None:
            u.email = data.email.strip()
        if data.activo is not None:
            nuevo = "1" if data.activo in ("1", 1, True, "true") else "0"
            if nuevo != "1" and (u.username == user.username or _es_superadmin(u)):
                raise HTTPException(status_code=400, detail="Ese usuario no se puede desactivar.")
            if nuevo != u.activo:
                u.activo = nuevo
                detalle["activo"] = nuevo
                if nuevo == "0":
                    u.sesiones_desde = datetime.utcnow()
        if data.password:
            motivo = validar_password(data.password)
            if motivo:
                raise HTTPException(status_code=400, detail=motivo)
            u.password_hash = hash_password(data.password)
            u.sesiones_desde = datetime.utcnow()
            detalle["password"] = "reseteada"
        db.commit()
        res = {"username": u.username, "nombre": u.nombre, "rol": rol_de(db, u.id), "activo": u.activo}
    finally:
        db.close()
    if "rol" in detalle:
        log_action(usuario=user.username, accion="ROLE_CHANGE", entidad="usuario", entidad_id=username,
                   detalle=detalle["rol"], ip=_ip(request))
    log_action(usuario=user.username, accion="modificacion_usuario", entidad="usuario", entidad_id=username,
               detalle={k: v for k, v in detalle.items() if k != "rol"} or None, ip=_ip(request))
    return res


@auth_router.delete("/usuarios/{username}")
def eliminar_usuario(username: str, request: Request, user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if u.username == user.username or _es_superadmin(u):
            raise HTTPException(status_code=400, detail="Ese usuario no se puede eliminar.")
        u.activo = "0"
        u.sesiones_desde = datetime.utcnow()
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="DELETE_USER", entidad="usuario", entidad_id=username, ip=_ip(request))
    return {"status": "ok"}


@auth_router.post("/cambiar-password")
def cambiar_password(data: ChangePassword, request: Request, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == user.username).first()
        if not u or not verify_password(data.password_actual, u.password_hash):
            raise HTTPException(status_code=400, detail="La contrasena actual es incorrecta.")
        motivo = validar_password(data.password_nuevo)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)
        u.password_hash = hash_password(data.password_nuevo)
        u.sesiones_desde = datetime.utcnow()
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="CHANGE_PASSWORD", entidad="usuario", entidad_id=user.username, ip=_ip(request))
    return {"status": "ok"}
