# -*- coding: utf-8 -*-
"""Envio de notificaciones por SMTP. Silencioso ante fallos: nunca rompe la operacion."""
import html, logging, smtplib, ssl, threading
from email.message import EmailMessage
from email.utils import formataddr
import config

_lock = threading.Lock()
log = logging.getLogger("inventario.mail")

def _cfg():
    return {
        "host": config.SMTP_HOST,
        "port": config.SMTP_PORT,
        "user": config.SMTP_USER,
        "pwd":  config.SMTP_PASS,
        "name": config.SMTP_FROM_NAME,
        "dom":  config.SMTP_DOMINIO,
        "url":  config.APP_URL,
    }

def _mails(usernames):
    """Convierte usernames en direcciones, sin duplicados ni vacios."""
    dom = _cfg()["dom"]
    out, vistos = [], set()
    for u in usernames or []:
        u = (u or "").strip().replace("TANGO\\", "").lower()
        if not u or u in vistos or u == "admin":
            continue
        vistos.add(u)
        out.append(u if "@" in u else "%s@%s" % (u, dom))
    return out

def enviar(destinatarios, asunto, cuerpo_html, cuerpo_txt=""):
    c = _cfg()
    dest = _mails(destinatarios)
    if not dest or not c["host"] or not c["user"] or not c["pwd"]:
        log.info("mail.omitido")
        return False
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = formataddr((c["name"], c["user"]))
    msg["To"] = ", ".join(dest)
    msg.set_content(cuerpo_txt or "Ver en %s" % c["url"])
    msg.add_alternative(cuerpo_html, subtype="html")
    with _lock:
        try:
            s = smtplib.SMTP(c["host"], c["port"], timeout=25)
            s.starttls(context=ssl.create_default_context())
            s.login(c["user"], c["pwd"])
            s.send_message(msg)
            s.quit()
            log.info("mail.enviado destinatarios=%d", len(dest))
            return True
        except Exception as e:
            log.error("mail.error %s", type(e).__name__)  # sin el texto: puede traer datos del servidor SMTP
            return False

def _html(titulo, lineas, pie=""):
    c = _cfg()
    filas = "".join("<p style='margin:6px 0;font-size:14px;color:#333'>%s</p>" % l for l in lineas)
    return """<html><body style="font-family:Segoe UI,Arial,sans-serif;background:#f4f6f8;padding:24px">
<div style="max-width:560px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e0e4e8">
  <div style="background:#0B7285;padding:16px 22px">
    <span style="color:#fff;font-size:16px;font-weight:600">%s</span>
  </div>
  <div style="padding:22px">
    %s
    <p style="margin-top:22px">
      <a href="%s/#proyectos" style="background:#00AEAE;color:#fff;text-decoration:none;padding:10px 20px;border-radius:5px;font-size:14px;display:inline-block">Ver en Inventario</a>
    </p>
    %s
  </div>
  <div style="background:#f7f9fa;padding:12px 22px;font-size:11.5px;color:#8a9199;border-top:1px solid #e0e4e8">
    Notificacion automatica - Inventario LLYA
  </div>
</div></body></html>""" % (titulo, filas, c["url"], pie)

def _e(v):
    """Escapa texto de usuario antes de meterlo en el HTML del mail."""
    return html.escape(str(v if v is not None else ""))


def notificar_tarea_completada(proyecto, tarea, quien, destinatarios):
    asunto = "[%s] Tarea completada: %s" % (proyecto.get("numero") or "Proyecto", tarea.get("titulo", "")[:60])
    lineas = [
        "<b>%s</b> completo una tarea." % _e(quien),
        "<b>Proyecto:</b> %s %s" % (_e(proyecto.get("numero", "")), _e(proyecto.get("nombre", ""))),
        "<b>Tarea:</b> %s" % _e(tarea.get("titulo", "")),
        "<b>Avance del proyecto:</b> %s%% (%s de %s tareas)" % (
            proyecto.get("avance_efectivo", 0), proyecto.get("tareas_hechas", 0), proyecto.get("tareas_total", 0)),
    ]
    return enviar(destinatarios, asunto, _html("Tarea completada", lineas))

def notificar_proyecto_finalizado(proyecto, quien, destinatarios):
    asunto = "[%s] Proyecto finalizado: %s" % (proyecto.get("numero") or "Proyecto", proyecto.get("nombre", "")[:60])
    lineas = [
        "<b>%s</b> marco el proyecto como finalizado." % _e(quien),
        "<b>Proyecto:</b> %s %s" % (_e(proyecto.get("numero", "")), _e(proyecto.get("nombre", ""))),
        "<b>Tareas:</b> %s de %s completadas" % (proyecto.get("tareas_hechas", 0), proyecto.get("tareas_total", 0)),
    ]
    if proyecto.get("descripcion"):
        lineas.append("<b>Descripcion:</b> %s" % _e(proyecto["descripcion"][:200]))
    return enviar(destinatarios, asunto, _html("Proyecto finalizado", lineas))