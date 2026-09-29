# audit.py - Helper de logging de auditoria
import json
from database import SessionLocal, AuditLog

def log_action(usuario, accion, entidad="", entidad_id="", detalle=None, ip="", resultado="success"):
    db = SessionLocal()
    entry = AuditLog(
        usuario=usuario or "",
        accion=accion,
        entidad=entidad or "",
        entidad_id=str(entidad_id) if entidad_id else "",
        detalle=json.dumps(detalle) if detalle else "",
        ip_origen=ip or "",
        resultado=resultado,
    )
    db.add(entry)
    db.commit()
    db.close()