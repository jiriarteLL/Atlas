# -*- coding: utf-8 -*-
"""Metricas Prometheus de la app (BEST_PRACTICES §6.2). Registro propio: no mezcla con otros procesos."""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import ProcessCollector, PlatformCollector

import config

REGISTRO = CollectorRegistry()
ProcessCollector(registry=REGISTRO)
PlatformCollector(registry=REGISTRO)

APP_INFO = Gauge("app_info", "Version de la app", ["app_slug", "version"], registry=REGISTRO)
APP_INFO.labels(config.APP_SLUG, config.APP_VERSION).set(1)

HTTP_REQUESTS = Counter("http_requests_total", "Requests HTTP", ["method", "route", "status"], registry=REGISTRO)
HTTP_DURACION = Histogram("http_request_duration_seconds", "Duracion de requests HTTP", ["method", "route"],
                          buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10), registry=REGISTRO)
LOGIN_INTENTOS = Counter("auth_login_attempts_total", "Intentos de login", registry=REGISTRO)
LOGIN_FALLOS = Counter("auth_login_failures_total", "Logins fallidos", ["motivo"], registry=REGISTRO)


def registrar_request(method, route, status, segundos):
    # route es la plantilla ("/api/assets/{aid}"), no la URL real: cardinalidad acotada y sin datos.
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_DURACION.labels(method, route).observe(segundos)


def metricas_texto():
    return generate_latest(REGISTRO), CONTENT_TYPE_LATEST
