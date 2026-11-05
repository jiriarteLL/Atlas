# -*- coding: utf-8 -*-
"""Login con el usuario de Windows del dominio (como Argos).

- La contrasena la valida el controlador de dominio con la API de Windows (LogonUserW, inicio de sesion de red).
  No se guarda en ningun lado ni se escribe en los logs.
- Solo funciona si Atlas corre en un Windows unido al dominio y AD_DOMINIO esta definido (p. ej. TANGO).
- Proteccion contra bloqueos: el dominio bloquea la cuenta al 3.er intento fallido (15 minutos). Atlas deja de
  probar al 2.o fallo del mismo usuario en 15 minutos, para no ser nunca el que bloquea la cuenta de Windows.
- Los usuarios de Windows quedan en la tabla users con MARCA como password_hash: no tienen contrasena local.
"""
import os
import re
import threading
import time

import config

MARCA = "!windows"          # password_hash de un usuario de Windows (passlib no lo reconoce: nunca valida local)
VENTANA = 15 * 60           # la misma ventana que usa el dominio para contar fallos
MAX_FALLOS = 2              # el dominio bloquea al 3.o: nunca llegar

ERRORES = {
    1326: "Usuario o contraseña de Windows incorrectos.",
    1909: "Tu cuenta de Windows está bloqueada por intentos fallidos. Esperá 15 minutos o pedile a Soporte que la desbloquee.",
    1331: "Tu cuenta de Windows está deshabilitada. Consultá con Soporte.",
    1330: "Tu contraseña de Windows venció. Cambiala desde tu PC (Ctrl+Alt+Supr) y volvé a intentar.",
    1907: "Tenés que cambiar tu contraseña de Windows antes de entrar. Cambiala desde tu PC y volvé a intentar.",
    1793: "Tu cuenta de Windows venció. Consultá con Soporte.",
    1327: "Tu cuenta tiene una restricción que no permite este inicio de sesión. Consultá con Soporte.",
    1328: "Tu cuenta no puede iniciar sesión en este horario.",
    1311: "No hay un controlador de dominio disponible. Probá en unos minutos o avisá a Soporte.",
}

_USUARIO_VALIDO = re.compile(r"^[A-Za-z0-9._\- ]{1,64}$")
_fallos = {}
_candado = threading.Lock()


def habilitado():
    return os.name == "nt" and bool(config.AD_DOMINIO)


def es_usuario_windows(u):
    return u is not None and u.password_hash == MARCA


def normalizar_usuario(texto):
    """'TANGO\\jperez', 'jperez@llasesores.corp' o 'jperez' -> 'jperez' (None si no es un usuario de Windows)."""
    t = (texto or "").strip()
    dominio = config.AD_DOMINIO.lower()
    sufijo = config.AD_SUFIJO_UPN
    if "\\" in t:
        d, _, t = t.partition("\\")
        if d.strip().lower() not in (dominio, sufijo.split(".")[0] if sufijo else dominio):
            return None
    elif "@" in t:
        t, _, s = t.partition("@")
        if not sufijo or s.strip().lower() != sufijo:
            return None
    t = t.strip()
    return t.lower() if _USUARIO_VALIDO.match(t) else None


def _logon_windows(usuario, clave):
    """(True, None) si Windows acepta la contrasena; (False, codigo de error) si no."""
    import ctypes
    from ctypes import wintypes
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    logon = advapi32.LogonUserW
    logon.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                      ctypes.POINTER(wintypes.HANDLE)]
    logon.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    ok = logon(usuario, config.AD_DOMINIO, clave, 3, 0, ctypes.byref(token))  # 3 = LOGON32_LOGON_NETWORK
    codigo = ctypes.get_last_error()
    if ok:
        kernel32.CloseHandle(token)
        return True, None
    return False, codigo


def _nombre_windows(usuario):
    """Nombre para mostrar desde el dominio (NetUserGetInfo nivel 10). Si falla, el usuario."""
    try:
        import ctypes
        from ctypes import wintypes
        netapi32 = ctypes.WinDLL("netapi32")
        dc = wintypes.LPWSTR()
        if netapi32.NetGetDCName(None, config.AD_DOMINIO, ctypes.byref(dc)) != 0:
            return usuario
        buf = ctypes.c_void_p()
        try:
            if netapi32.NetUserGetInfo(dc, usuario, 10, ctypes.byref(buf)) != 0:
                return usuario

            class USER_INFO_10(ctypes.Structure):
                _fields_ = [("name", wintypes.LPWSTR), ("comment", wintypes.LPWSTR),
                            ("usr_comment", wintypes.LPWSTR), ("full_name", wintypes.LPWSTR)]

            info = ctypes.cast(buf, ctypes.POINTER(USER_INFO_10)).contents
            return (info.full_name or "").strip() or usuario
        finally:
            if buf:
                netapi32.NetApiBufferFree(buf)
            netapi32.NetApiBufferFree(dc)
    except Exception:  # noqa: BLE001
        return usuario


# Se reemplazan en los tests (no hay dominio en CI).
validar = _logon_windows
nombre_completo = _nombre_windows


def _recientes(usuario, ahora):
    lista = [t for t in _fallos.get(usuario, []) if ahora - t < VENTANA]
    _fallos[usuario] = lista
    return lista


def bloqueo_previo(usuario):
    """Mensaje si ya no se debe probar contra el dominio (2 fallos en 15 min); None si se puede."""
    ahora = time.time()
    with _candado:
        lista = _recientes(usuario, ahora)
        if len(lista) >= MAX_FALLOS:
            minutos = max(1, int((VENTANA - (ahora - min(lista))) // 60) + 1)
            return ("Por seguridad no se prueba de nuevo: el dominio bloquea la cuenta de Windows al tercer intento "
                    "fallido. Esperá %d minutos o pedile a Soporte que verifique tu contraseña." % minutos)
    return None


def registrar_fallo(usuario, codigo):
    """Cuenta el fallo (si fue de contrasena) y devuelve el mensaje para la persona."""
    if codigo not in (1326, None):
        return ERRORES.get(codigo, "Windows no aceptó el inicio de sesión (código %s). Consultá con Soporte." % codigo)
    ahora = time.time()
    with _candado:
        _fallos.setdefault(usuario, []).append(ahora)
        quedan = MAX_FALLOS - len(_recientes(usuario, ahora))
    if quedan <= 0:
        return ERRORES[1326] + " Para no bloquear tu cuenta de Windows, Atlas no va a probar de nuevo por 15 minutos."
    return ERRORES[1326] + " Ojo: al tercer intento fallido Windows bloquea la cuenta por 15 minutos."


def limpiar(usuario=None):
    with _candado:
        if usuario is None:
            _fallos.clear()
        else:
            _fallos.pop(usuario, None)
