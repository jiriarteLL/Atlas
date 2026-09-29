# auth.py - Autenticacion simple con usuarios en BD
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from audit import log_action
from ratelimit import limiter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import SessionLocal, Base
from sqlalchemy import Column, String, DateTime
import uuid

from dotenv import load_dotenv
load_dotenv(r"C:/AssetManager/backend/.env")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Modelo de usuario en BD
class User(Base):
    __tablename__ = "users"
    id       = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    nombre   = Column(String, default="")
    rol      = Column(String, default="viewer")  # admin | editor | viewer
    activo   = Column(String, default="1")
    email    = Column(String, default="")
    created  = Column(DateTime, default=datetime.utcnow)

class UserOut(BaseModel):
    username: str
    nombre: str
    rol: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut

class UserCreate(BaseModel):
    username: str
    password: str
    nombre: str
    rol: str = "soporte"

class UserUpdate(BaseModel):
    nombre:   Optional[str] = None
    email:    Optional[str] = None
    rol:      Optional[str] = None
    activo:   Optional[str] = None
    password: Optional[str] = None

class ChangePassword(BaseModel):
    password_actual: str
    password_nuevo: str

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user: UserOut) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user.username, "nombre": user.nombre, "rol": user.rol, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return UserOut(username=payload["sub"], nombre=payload.get("nombre",""), rol=payload.get("rol","soporte"))
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado.")

def require_admin(user: UserOut = Depends(get_current_user)) -> UserOut:
    if user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol admin.")
    return user

def require_escritura(user: UserOut = Depends(get_current_user)) -> UserOut:
    """Cualquier usuario logueado salvo viewer (solo lectura)."""
    if user.rol == "viewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu rol es de solo lectura.")
    return user

@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip = request.client.host if request.client else ""
    db = SessionLocal()
    user = db.query(User).filter(User.username == form_data.username, User.activo == "1").first()
    db.close()
    if not user or not verify_password(form_data.password, user.password):
        log_action(usuario=form_data.username, accion="LOGIN_FAILED", ip=ip, resultado="failure")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contrasena incorrectos.")
    user_out = UserOut(username=user.username, nombre=user.nombre, rol=user.rol)
    token = create_token(user_out)
    log_action(usuario=user.username, accion="LOGIN_SUCCESS", ip=ip, resultado="success")
    return TokenResponse(access_token=token, expires_in=JWT_EXPIRE_MINUTES*60, user=user_out)

@auth_router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    return user

PERMISOS = {
    "admin":  ["Ver inventario", "Crear y editar activos", "Eliminar activos",
               "Gestionar proyectos y tareas", "Ver y editar licencias",
               "Administrar usuarios y roles", "Consultar garantias"],
    "editor": ["Ver inventario", "Crear y editar activos", "Eliminar activos",
               "Gestionar proyectos y tareas", "Ver y editar licencias",
               "Consultar garantias"],
    "viewer": ["Ver inventario", "Ver proyectos", "Ver licencias"],
}

@auth_router.get("/perfil")
def perfil(user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    u = db.query(User).filter(User.username == user.username).first()
    db.close()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    ultimos = []
    try:
        from database import AuditLog
        db2 = SessionLocal()
        for a in (db2.query(AuditLog)
                  .filter(AuditLog.usuario == user.username)
                  .order_by(AuditLog.timestamp.desc()).limit(8).all()):
            ultimos.append({"fecha": str(a.timestamp)[:19], "accion": a.accion,
                            "entidad": a.entidad or "", "ip": a.ip_origen or ""})
        db2.close()
    except Exception:
        pass
    return {"username": u.username, "nombre": u.nombre or "", "email": u.email or "",
            "rol": u.rol, "activo": u.activo, "creado": str(u.created or "")[:19],
            "permisos": PERMISOS.get(u.rol, []), "actividad": ultimos}

@auth_router.put("/perfil")
def editar_perfil(data: UserUpdate, user: UserOut = Depends(get_current_user)):
    """Cada usuario puede editar su propio nombre y email. Rol y estado no."""
    db = SessionLocal()
    u = db.query(User).filter(User.username == user.username).first()
    if not u:
        db.close(); raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if data.nombre is not None and data.nombre.strip():
        u.nombre = data.nombre.strip()
    if data.email is not None:
        u.email = data.email.strip()
    db.commit()
    res = {"username": u.username, "nombre": u.nombre, "email": u.email or "", "rol": u.rol}
    db.close()
    return res

@auth_router.post("/usuarios")
def crear_usuario(data: UserCreate, user: UserOut = Depends(require_admin), request: Request = None):
    db = SessionLocal()
    existe = db.query(User).filter(User.username == data.username).first()
    if existe:
        db.close()
        raise HTTPException(status_code=400, detail="El usuario ya existe.")
    nuevo = User(username=data.username, password=hash_password(data.password), nombre=data.nombre, rol=data.rol)
    db.add(nuevo); db.commit(); db.close()
    ip = request.client.host if request.client else ""
    log_action(usuario=user.username, accion="CREATE_USER", entidad="usuario", entidad_id=data.username, ip=ip)
    return {"status": "ok", "username": data.username}

@auth_router.get("/usuarios")
def listar_usuarios(user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return [{"username": u.username, "nombre": u.nombre, "email": u.email or "", "rol": u.rol, "activo": u.activo} for u in users]

@auth_router.put("/usuarios/{username}")
def editar_usuario(username: str, data: UserUpdate, user: UserOut = Depends(require_admin), request: Request = None):
    ROLES = ("admin", "editor", "viewer")
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if data.rol is not None:
        if data.rol not in ROLES:
            db.close()
            raise HTTPException(status_code=400, detail="Rol invalido.")
        if u.username == user.username and data.rol != "admin":
            db.close()
            raise HTTPException(status_code=400, detail="No podes quitarte a vos mismo el rol admin.")
        u.rol = data.rol
    if data.nombre is not None and data.nombre.strip():
        u.nombre = data.nombre.strip()
    if data.email is not None:
        u.email = data.email.strip()
    if data.activo is not None:
        if u.username == user.username and data.activo != "1":
            db.close()
            raise HTTPException(status_code=400, detail="No podes desactivar tu propio usuario.")
        u.activo = "1" if data.activo in ("1", 1, True, "true") else "0"
    if data.password:
        u.password = hash_password(data.password)
    db.commit()
    res = {"username": u.username, "nombre": u.nombre, "rol": u.rol, "activo": u.activo}
    db.close()
    ip = request.client.host if (request and request.client) else ""
    log_action(usuario=user.username, accion="modificacion_usuario", entidad="user",
               entidad_id=username, ip=ip, resultado="success")
    return res

@auth_router.delete("/usuarios/{username}")
def eliminar_usuario(username: str, user: UserOut = Depends(require_admin), request: Request = None):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        db.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    u.activo = "0"
    db.commit(); db.close()
    ip = request.client.host if request.client else ""
    log_action(usuario=user.username, accion="DELETE_USER", entidad="usuario", entidad_id=username, ip=ip)
    return {"status": "ok"}

@auth_router.post("/cambiar-password")
def cambiar_password(data: ChangePassword, user: UserOut = Depends(get_current_user), request: Request = None):
    db = SessionLocal()
    u = db.query(User).filter(User.username == user.username).first()
    if not u or not verify_password(data.password_actual, u.password):
        db.close()
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    u.password = hash_password(data.password_nuevo)
    db.commit()
    db.close()
    ip = request.client.host if request.client else ""
    log_action(usuario=user.username, accion="CHANGE_PASSWORD", entidad="usuario", entidad_id=user.username, ip=ip)
    return {"status": "ok"}