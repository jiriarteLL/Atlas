# Inventario LLYA v2 — imagen unica: el backend FastAPI sirve el frontend compilado.
# Requisitos: SPEC §2.2 / CONVENCIONES §8 / README §12 (multi-stage, no-root, EXPOSE, HEALTHCHECK, CMD).

# ── Stage 1: build del frontend ──
# Imagenes base fijadas por digest (09-SEGURIDAD capa 7); actualizar con el tag + digest nuevos.
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS frontend
WORKDIR /build
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/frontend/ ./
RUN npx vite build --outDir /build/dist

# ── Stage 2: dependencias de Python ──
FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e AS pydeps
COPY app/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# ── Stage 3: runtime ──
FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend_dist \
    AGENTE_DIR=/app/agente
WORKDIR /app

# 1. Usuario no-root
RUN groupadd --system --gid 1001 appgroup && useradd --system --uid 1001 --gid appgroup --no-create-home appuser

# 2. Solo lo necesario
COPY --from=pydeps /install /usr/local
COPY app/backend/ ./backend/
COPY agente/agent_linux.sh ./agente/agent_linux.sh
COPY --from=frontend /build/dist ./frontend_dist
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

# 3. Sin volumenes: el filesystem es efimero y el estado va a la base (CONVENCIONES §4.2, ADR-001).
#    El contenedor corre con read_only y solo /tmp escribible (tmpfs en los compose).

# 4. Puerto interno fijo (= requires.ports.app de maestro.yaml)
EXPOSE 8000

# 5. No-root
USER appuser

# 6. Health check (sin curl en la imagen slim: se usa Python)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# 7. Inicio: migracion + seeder (falla si la password del superadmin es debil) y despues la app
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
