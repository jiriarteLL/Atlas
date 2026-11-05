# -*- coding: utf-8 -*-
"""Contexto por request (request_id, ip, user-agent, usuario) y logs JSON a stdout.

CONVENCIONES §10.1: timestamp, level, message, request_id, user_id, app_slug.
CONVENCIONES §10.2: nunca loguear passwords, hashes, tokens, api keys ni cookies.

El contexto es UN dict mutable por request: las dependencias sincronas corren en un threadpool con
una copia del contexto, pero la copia apunta al mismo dict, asi que el user_id que fija
get_current_user tambien lo ve el log del middleware.
"""
import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

import config

_ctx = ContextVar("ctx_request", default=None)
_REQ_ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
# Por si algo sensible llega a un mensaje: se tapa antes de escribir.
_SENSIBLE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]+|((?:password|passwd|secret|token|api[_-]?key)[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+")


def actual():
    """Contexto del request en curso ({} fuera de un request)."""
    return _ctx.get() or {}


def fijar_usuario(user_id, username):
    c = _ctx.get()
    if c is not None:
        c["user_id"], c["username"] = user_id or "", username or ""


def _tapar(texto):
    return _SENSIBLE.sub(lambda m: (m.group(1) or m.group(2)) + "***", texto)


class FormatoJSON(logging.Formatter):
    def format(self, record):
        c = actual()
        d = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "message": _tapar(record.getMessage()),
            "request_id": c.get("request_id", ""),
            "user_id": c.get("user_id", ""),
            "app_slug": config.APP_SLUG,
            "app_version": config.APP_VERSION,
            "logger": record.name,
        }
        for k in ("method", "path", "status", "duration_ms", "event"):
            if hasattr(record, k):
                d[k] = getattr(record, k)
        if record.exc_info:
            d["exception"] = _tapar(self.formatException(record.exc_info))
        return json.dumps(d, ensure_ascii=False)


def configurar_logs():
    raiz = logging.getLogger()
    raiz.handlers.clear()
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(FormatoJSON() if config.LOG_FORMAT == "json" else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    raiz.addHandler(h)
    raiz.setLevel(config.LOG_LEVEL.upper())
    # El access log de uvicorn se reemplaza por el del middleware (con request_id y sin query strings).
    for nombre in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(nombre)
        lg.handlers.clear()
        lg.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


log = logging.getLogger("atlas")


class ContextoMiddleware:
    """ASGI puro: arma el contexto, devuelve X-Request-Id y loguea cada request (sin query string ni headers)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        rid = headers.get("x-request-id", "")
        rid = rid if _REQ_ID_OK.match(rid) else "req_" + uuid.uuid4().hex
        token = _ctx.set({"request_id": rid, "ip": (scope.get("client") or ("", 0))[0] or "",
                          "user_agent": headers.get("user-agent", "")[:300], "user_id": "", "username": ""})
        inicio = time.perf_counter()
        estado = {"code": 500}

        async def enviar(msg):
            if msg["type"] == "http.response.start":
                estado["code"] = msg["status"]
                msg.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(msg)

        try:
            await self.app(scope, receive, enviar)
        finally:
            ruta = scope.get("path", "")
            if ruta != "/health" or estado["code"] != 200:  # el health se consulta cada 30 s: no llenar el log
                log.info("http.request", extra={"event": "http.request", "method": scope.get("method"), "path": ruta,
                                                "status": estado["code"],
                                                "duration_ms": round((time.perf_counter() - inicio) * 1000, 1)})
            _ctx.reset(token)
