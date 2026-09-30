# -*- coding: utf-8 -*-
"""Login propio de la app (SPEC §2.4, Premisa 7, 03-AUTENTICACION).

- users + roles + permissions (+ pivots user_roles / role_permissions).
- Access token JWT corto (TOKEN_TTL, 15 min) que el frontend guarda solo en memoria.
- Refresh token opaco y rotativo (REFRESH_TOKEN_TTL) en cookie HttpOnly + SameSite=Strict, Path=/auth,
  guardado hasheado en la base. Reusar un refresh ya rotado revoca todas las sesiones del usuario.
- Logout revoca el access (jti) y el refresh. Cambiar password o desactivar invalida todo lo anterior.
- Login: 5/min por IP, 10/h por email, bloqueo de 15 min tras 5 fallos seguidos. Mensaje de error unico.
"""
import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
import jwt   # PyJWT (python-jose arrastraba ecdsa, CVE-2024-23342 sin fix)
from jwt import PyJWTError as JWTError
from limits import parse as parse_limite
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

import config
import contexto
from audit import log_action
from database import Base, SessionLocal
from metricas import LOGIN_FALLOS, LOGIN_INTENTOS
from ratelimit import limiter

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=config.BCRYPT_COST)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
auth_router = APIRouter(prefix="/auth", tags=["auth"])
login_router = APIRouter(tags=["auth"])   # /login y /logout de maestro.yaml (auth.login_path / logout_path)

_ERROR_LOGIN = "Usuario o contrasena incorrectos."


# ---------------------------------------------------------------- modelos
class User(Base):
    __tablename__ = "users"
    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username       = Column(String, unique=True, nullable=False)
    email          = Column(String, unique=True, nullable=True)   # SPEC §3: usuarios identificables por email unico
    password_hash  = Column(String, nullable=False)
    nombre         = Column(String, default="")
    activo         = Column(String, default="1")
    created        = Column(DateTime, default=datetime.utcnow)
    last_login_at  = Column(DateTime, nullable=True)
    # Tokens emitidos antes de esta fecha dejan de valer (cambio de password, desactivacion).
    sesiones_desde = Column(DateTime, nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta   = Column(DateTime, nullable=True)
    # El superadmin sembrado tiene que cambiar la password inicial (09-SEGURIDAD capa 4). Lo exige la UI.
    debe_cambiar_password = Column(Boolean, default=False)


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


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False)   # sha256 del token; el token nunca se guarda
    creado     = Column(DateTime, default=datetime.utcnow)
    expira     = Column(DateTime, nullable=False)
    revocado   = Column(Boolean, default=False)


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
_BLACKLIST_BASE = {"admin", "password", "123456789012", "contrasena", "contraseña", "qwertyuiop", "llyasoc",
                   "administrador", "password1234", "admin1234567", "passw0rd", "cambiar", "inventario"}


def _cargar_blacklist():
    """Blacklist base + lista de passwords comunes (passwords_comunes.txt, una por linea) si esta en la imagen."""
    s = set(_BLACKLIST_BASE)
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "passwords_comunes.txt")
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            s.update(l.strip().lower() for l in f if l.strip())
    return s


_BLACKLIST = _cargar_blacklist()


def validar_password(p):
    """Devuelve None si la password es aceptable, o el motivo del rechazo."""
    p = p or ""
    pl = p.lower()
    if len(p) < 12:
        return "La contrasena debe tener al menos 12 caracteres."
    if len(p) > 128:
        return "La contrasena no puede superar 128 caracteres."
    if pl in _BLACKLIST or any(pl.startswith(b) and len(set(pl[len(b):])) <= 1 for b in _BLACKLIST_BASE):
        return "La contrasena es demasiado comun."
    if "cambiar" in pl:
        return "La contrasena parece el valor de ejemplo de .env.example."
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


# Hash valido para comparar cuando el usuario no existe: el login tarda lo mismo y no revela que emails existen.
_HASH_SEÑUELO = hash_password(secrets.token_urlsafe(24))

_EMAIL_OK = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _email(v):
    v = (v or "").strip().lower()
    if not _EMAIL_OK.match(v):
        raise HTTPException(status_code=400, detail="Email invalido.")
    return v


# ---------------------------------------------------------------- schemas
class UserOut(BaseModel):
    id: str = ""
    username: str
    nombre: str
    rol: str
    email: str = ""
    permisos: List[str] = []
    debe_cambiar_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    nombre: str
    email: str
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


# ---------------------------------------------------------------- tokens
def _ahora():
    return datetime.now(timezone.utc)


def _utc_naive(dt):
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def create_token(user, sid=None) -> str:
    ahora = _ahora()
    # "ms": emision en milisegundos, para comparar contra sesiones_desde sin perder precision.
    # "sid": id del refresh token de esta sesion; el logout lo revoca aunque no llegue la cookie (Path=/auth).
    payload = {"sub": user.username, "uid": user.id, "jti": str(uuid.uuid4()), "iat": int(ahora.timestamp()),
               "ms": int(ahora.timestamp() * 1000), "exp": ahora + timedelta(minutes=config.TOKEN_TTL_MIN)}
    if sid:
        payload["sid"] = sid
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _decodificar(token):
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado.")


def _sha(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _emitir_refresh(db, user, response):
    """Crea el refresh, lo manda en la cookie y devuelve su id (va como "sid" en el access token)."""
    token = secrets.token_urlsafe(48)
    sid = str(uuid.uuid4())
    db.add(RefreshToken(id=sid, user_id=user.id, token_hash=_sha(token),
                        expira=_utc_naive(_ahora() + timedelta(minutes=config.REFRESH_TOKEN_TTL_MIN))))
    response.set_cookie(config.COOKIE_SESION, token, max_age=config.REFRESH_TOKEN_TTL_MIN * 60, path="/auth",
                        httponly=True, secure=config.COOKIES_SEGURAS, samesite="strict")
    return sid


def _borrar_cookie(response):
    response.delete_cookie(config.COOKIE_SESION, path="/auth", httponly=True, secure=config.COOKIES_SEGURAS,
                           samesite="strict")


def revocar_sesiones(db, user):
    """Invalida todos los access y refresh vigentes del usuario."""
    user.sesiones_desde = datetime.utcnow()
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revocado.is_(False)) \
        .update({RefreshToken.revocado: True}, synchronize_session=False)


def _sesion_vigente(user, emitido_ms):
    if user.activo != "1":
        return False
    if user.sesiones_desde and emitido_ms <= int(user.sesiones_desde.replace(tzinfo=timezone.utc).timestamp() * 1000):
        return False
    return True


def _user_out(db, u):
    return UserOut(id=u.id, username=u.username, nombre=u.nombre or "", email=u.email or "",
                   rol=rol_de(db, u.id), permisos=permisos_de(db, u.id),
                   debe_cambiar_password=bool(u.debe_cambiar_password))


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    payload = _decodificar(token)
    no_valido = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado.")
    db = SessionLocal()
    try:
        if not payload.get("jti") or db.get(RevokedToken, payload["jti"]):
            raise no_valido
        u = db.query(User).filter(User.username == payload.get("sub")).first()
        if not u or not _sesion_vigente(u, payload.get("ms", 0)):
            raise no_valido
        contexto.fijar_usuario(u.id, u.username)
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


# ---------------------------------------------------------------- login
_limite_email = parse_limite("%d/hour" % config.LOGIN_RATE_LIMIT_PER_EMAIL)
_limitador_email = MovingWindowRateLimiter(MemoryStorage())


def reiniciar_limites():
    """Para los tests: vacia los contadores de login."""
    _limitador_email.storage.reset()
    limiter.reset()


async def _credenciales(request):
    """Acepta form (username/password, lo que manda el frontend) o JSON (email|username|usuario + password)."""
    if "application/json" in (request.headers.get("content-type") or ""):
        try:
            d = await request.json()
        except ValueError:
            d = {}
        d = d if isinstance(d, dict) else {}
        ident = d.get("email") or d.get("username") or d.get("usuario") or ""
        return str(ident).strip(), str(d.get("password") or "")
    f = await request.form()
    return str(f.get("username") or f.get("email") or "").strip(), str(f.get("password") or "")


def _fallo(ident, motivo="credenciales"):
    LOGIN_FALLOS.labels(motivo).inc()
    log_action(usuario=ident, accion="LOGIN_FAILED", resultado="failure")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_ERROR_LOGIN)


async def login(request: Request, response: Response):
    LOGIN_INTENTOS.inc()
    ident, password = await _credenciales(request)
    if not _limitador_email.hit(_limite_email, "login-email", ident.lower()):
        LOGIN_FALLOS.labels("rate_limit_email").inc()
        log_action(usuario=ident, accion="LOGIN_RATE_LIMITED", resultado="failure")
        raise HTTPException(status_code=429, detail="Demasiados intentos. Proba mas tarde.")
    if not ident or not password:
        _fallo(ident)
    db = SessionLocal()
    try:
        u = (db.query(User).filter((User.username == ident) | (User.email == ident.lower())).first())
        ok = verify_password(password, u.password_hash if u else _HASH_SEÑUELO)
        if not u or u.activo != "1":
            _fallo(ident)
        if u.bloqueado_hasta and u.bloqueado_hasta > datetime.utcnow():
            LOGIN_FALLOS.labels("cuenta_bloqueada").inc()
            log_action(usuario=u.username, user_id=u.id, accion="LOGIN_LOCKED", resultado="failure")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_ERROR_LOGIN)
        if not ok:
            u.intentos_fallidos = (u.intentos_fallidos or 0) + 1
            if u.intentos_fallidos >= config.LOGIN_MAX_FALLOS:
                u.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=config.LOGIN_BLOQUEO_MIN)
                u.intentos_fallidos = 0
                db.commit()
                log_action(usuario=u.username, user_id=u.id, accion="ACCOUNT_LOCKED", resultado="failure",
                           detalle={"minutos": config.LOGIN_BLOQUEO_MIN})
            db.commit()
            _fallo(ident)
        u.intentos_fallidos, u.bloqueado_hasta, u.last_login_at = 0, None, datetime.utcnow()
        sid = _emitir_refresh(db, u, response)
        db.commit()
        out = _user_out(db, u)
        access = create_token(u, sid)
    finally:
        db.close()
    log_action(usuario=out.username, user_id=out.id, accion="LOGIN_SUCCESS")
    return TokenResponse(access_token=access, expires_in=config.TOKEN_TTL_MIN * 60, user=out)


login = limiter.shared_limit("%d/minute" % config.LOGIN_RATE_LIMIT_PER_IP, scope="login")(login)
auth_router.add_api_route("/login", login, methods=["POST"], response_model=TokenResponse)
login_router.add_api_route("/login", login, methods=["POST"], response_model=TokenResponse)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response):
    """Canjea el refresh de la cookie por un access nuevo y rota el refresh.
    Exige X-Requested-With (un sitio ajeno no puede mandarlo sin preflight CORS) ademas de SameSite=Strict."""
    no_valido = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion vencida.")
    if not request.headers.get("x-requested-with"):
        raise no_valido
    token = request.cookies.get(config.COOKIE_SESION, "")
    if not token:
        raise no_valido
    db = SessionLocal()
    try:
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == _sha(token)).first()
        if not rt:
            _borrar_cookie(response)
            raise no_valido
        u = db.get(User, rt.user_id)
        if rt.revocado:
            # Reuso de un refresh ya rotado: posible robo. Se cortan todas las sesiones del usuario.
            if u:
                revocar_sesiones(db, u)
                db.commit()
                log_action(usuario=u.username, user_id=u.id, accion="REFRESH_REUSE", resultado="failure")
            raise no_valido
        creado_ms = int(rt.creado.replace(tzinfo=timezone.utc).timestamp() * 1000)
        if rt.expira < datetime.utcnow() or not u or not _sesion_vigente(u, creado_ms):
            rt.revocado = True
            db.commit()
            raise no_valido
        rt.revocado = True
        sid = _emitir_refresh(db, u, response)
        db.commit()
        contexto.fijar_usuario(u.id, u.username)
        out = _user_out(db, u)
        access = create_token(u, sid)
    finally:
        db.close()
    return TokenResponse(access_token=access, expires_in=config.TOKEN_TTL_MIN * 60, user=out)


def logout(request: Request, response: Response, token: str = Depends(oauth2_scheme),
           user: UserOut = Depends(get_current_user)):
    payload = _decodificar(token)
    db = SessionLocal()
    try:
        db.query(RevokedToken).filter(RevokedToken.expira < datetime.utcnow()).delete()
        db.add(RevokedToken(jti=payload["jti"], expira=datetime.utcfromtimestamp(payload["exp"])))
        # El refresh de esta sesion se revoca por el "sid" del access (POST /logout no recibe la cookie,
        # que es Path=/auth) y, si llega, tambien por la cookie.
        sesion = RefreshToken.id == payload.get("sid", "")
        cookie = request.cookies.get(config.COOKIE_SESION, "")
        if cookie:
            sesion = sesion | (RefreshToken.token_hash == _sha(cookie))
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id, sesion) \
            .update({RefreshToken.revocado: True}, synchronize_session=False)
        db.query(RefreshToken).filter(RefreshToken.expira < datetime.utcnow()).delete()
        db.commit()
    finally:
        db.close()
    _borrar_cookie(response)
    log_action(usuario=user.username, accion="LOGOUT")
    return {"status": "ok"}


auth_router.add_api_route("/logout", logout, methods=["POST"])
login_router.add_api_route("/logout", logout, methods=["POST"])


# ---------------------------------------------------------------- perfil
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


def _email_libre(db, email, excepto_id=None):
    q = db.query(User).filter(User.email == email)
    if excepto_id:
        q = q.filter(User.id != excepto_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Ese email ya esta en uso.")


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
        if data.email is not None and u.username != config.SUPERADMIN_EMAIL:
            nuevo = _email(data.email)
            _email_libre(db, nuevo, u.id)
            u.email = nuevo
        db.commit()
        return {"username": u.username, "nombre": u.nombre, "email": u.email or "", "rol": user.rol}
    finally:
        db.close()


# ---------------------------------------------------------------- administracion de usuarios
@auth_router.post("/usuarios")
def crear_usuario(data: UserCreate, user: UserOut = Depends(require_admin)):
    if data.rol not in ROLES_ASIGNABLES:
        raise HTTPException(status_code=400, detail="Rol invalido.")
    motivo = validar_password(data.password)
    if motivo:
        raise HTTPException(status_code=400, detail=motivo)
    email = _email(data.email)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == data.username.strip()).first():
            raise HTTPException(status_code=400, detail="El usuario ya existe.")
        _email_libre(db, email)
        nuevo = User(username=data.username.strip(), password_hash=hash_password(data.password),
                     nombre=data.nombre, email=email)
        db.add(nuevo)
        db.flush()
        asignar_rol(db, nuevo, data.rol)
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="CREATE_USER", entidad="usuario", entidad_id=data.username,
               detalle={"rol": data.rol})
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
def editar_usuario(username: str, data: UserUpdate, user: UserOut = Depends(require_admin)):
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
        if data.email is not None and not _es_superadmin(u):
            nuevo = _email(data.email)
            _email_libre(db, nuevo, u.id)
            u.email = nuevo
        if data.activo is not None:
            nuevo = "1" if data.activo in ("1", 1, True, "true") else "0"
            if nuevo != "1" and (u.username == user.username or _es_superadmin(u)):
                raise HTTPException(status_code=400, detail="Ese usuario no se puede desactivar.")
            if nuevo != u.activo:
                u.activo = nuevo
                detalle["activo"] = nuevo
                if nuevo == "0":
                    revocar_sesiones(db, u)
        if data.password:
            motivo = validar_password(data.password)
            if motivo:
                raise HTTPException(status_code=400, detail=motivo)
            u.password_hash = hash_password(data.password)
            u.debe_cambiar_password = True   # password puesta por un admin: el usuario la cambia al entrar
            revocar_sesiones(db, u)
            detalle["password"] = "reseteada"
        db.commit()
        res = {"username": u.username, "nombre": u.nombre, "rol": rol_de(db, u.id), "activo": u.activo}
    finally:
        db.close()
    if "rol" in detalle:
        log_action(usuario=user.username, accion="ROLE_CHANGE", entidad="usuario", entidad_id=username,
                   detalle=detalle["rol"])
    log_action(usuario=user.username, accion="modificacion_usuario", entidad="usuario", entidad_id=username,
               detalle={k: v for k, v in detalle.items() if k != "rol"} or None)
    return res


@auth_router.delete("/usuarios/{username}")
def eliminar_usuario(username: str, user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if u.username == user.username or _es_superadmin(u):
            raise HTTPException(status_code=400, detail="Ese usuario no se puede eliminar.")
        u.activo = "0"
        revocar_sesiones(db, u)
        db.commit()
    finally:
        db.close()
    log_action(usuario=user.username, accion="DELETE_USER", entidad="usuario", entidad_id=username)
    return {"status": "ok"}


@auth_router.post("/cambiar-password")
def cambiar_password(data: ChangePassword, response: Response, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == user.username).first()
        if not u or not verify_password(data.password_actual, u.password_hash):
            raise HTTPException(status_code=400, detail="La contrasena actual es incorrecta.")
        if data.password_nuevo == data.password_actual:
            raise HTTPException(status_code=400, detail="La contrasena nueva tiene que ser distinta de la actual.")
        motivo = validar_password(data.password_nuevo)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)
        u.password_hash = hash_password(data.password_nuevo)
        u.debe_cambiar_password = False
        revocar_sesiones(db, u)
        db.commit()
    finally:
        db.close()
    _borrar_cookie(response)
    log_action(usuario=user.username, accion="CHANGE_PASSWORD", entidad="usuario", entidad_id=user.username)
    return {"status": "ok"}
