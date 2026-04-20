# ============================================================================
# Maestro Platform — Dockerfile del portal React (Vite + TypeScript)
# Multi-stage: dev (HMR) y prod (nginx static)
# ============================================================================

# ----- Stage base -----
# node:20-alpine ya trae usuario 'node' con UID/GID 1000. Lo removemos y creamos 'app' con el mismo UID.
FROM node:20-alpine AS base
RUN apk add --no-cache tini \
    && deluser node 2>/dev/null || true \
    && addgroup -g 1000 -S app \
    && adduser -u 1000 -S app -G app -h /home/app -s /bin/sh
WORKDIR /app
RUN chown -R app:app /app
ENV NODE_ENV=development

# ----- Stage dev -----
FROM base AS dev
USER app
EXPOSE 8081
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8081"]

# ----- Stage build -----
FROM base AS build
COPY --chown=app:app portal/package*.json ./
USER app
RUN npm ci
COPY --chown=app:app portal ./
RUN NODE_ENV=production npm run build

# ----- Stage prod (nginx static) -----
FROM nginx:1.27-alpine AS prod
COPY docker/portal/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
RUN addgroup -g 1000 -S app \
    && adduser -u 1000 -S app -G app \
    && chown -R app:app /var/cache/nginx /var/log/nginx /usr/share/nginx/html
USER app
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O- http://127.0.0.1:8081/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
