# audit.py - Audit log (solo INSERT; en PostgreSQL un trigger rechaza UPDATE/DELETE)
import json
import logging

import contexto
from database import SessionLocal, AuditLog

log = logging.getLogger("atlas.audit")


def log_action(usuario, accion, entidad="", entidad_id="", detalle=None, ip="", resultado="success", user_id=""):
    """Registra un evento. IP, user-agent y user_id salen del contexto del request si no se pasan."""
    c = contexto.actual()
    entry = AuditLog(
        usuario=usuario or "",
        user_id=user_id or c.get("user_id", ""),
        accion=accion,
        entidad=entidad or "",
        entidad_id=str(entidad_id) if entidad_id else "",
        detalle=json.dumps(detalle, ensure_ascii=False, default=str) if detalle else "",
        ip_origen=ip or c.get("ip", ""),
        user_agent=c.get("user_agent", ""),
        request_id=c.get("request_id", ""),
        resultado=resultado,
    )
    db = SessionLocal()
    try:
        db.add(entry)
        db.commit()
    finally:
        db.close()
    log.info("audit.%s", accion.lower(), extra={"event": "audit"})
