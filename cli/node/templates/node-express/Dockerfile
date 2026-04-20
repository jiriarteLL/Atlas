# Multi-stage obligatorio (CONVENCIONES_PLATAFORMA §8)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

FROM node:20-alpine AS runtime
WORKDIR /app

# No-negociable 4: usuario no-root
RUN addgroup -g 1001 -S app && adduser -u 1001 -S app -G app
USER app

COPY --from=deps --chown=app:app /app/node_modules ./node_modules
COPY --chown=app:app src ./src
COPY --chown=app:app package.json ./

EXPOSE 3000

# No-negociable 3: HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O- http://localhost:3000/health || exit 1

CMD ["node", "src/index.js"]
