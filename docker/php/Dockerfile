# ============================================================================
# Maestro Platform — Dockerfile del backend (Laravel 13 + PHP 8.3)
# Multi-stage: base → dev (con tooling) / prod (slim)
# Non-root por defecto (no-negociable 4 + CIS Docker)
# ============================================================================

# ----- Stage base -----
FROM php:8.3-fpm-alpine AS base

# Dependencias del sistema necesarias para PHP extensions
RUN apk add --no-cache \
        bash \
        curl \
        git \
        icu-dev \
        libpq \
        libpq-dev \
        libzip-dev \
        oniguruma-dev \
        postgresql-client \
        redis \
        tzdata \
        zip \
        unzip \
    && apk add --no-cache --virtual .build-deps \
        autoconf \
        g++ \
        make \
    && docker-php-ext-install \
        bcmath \
        intl \
        mbstring \
        opcache \
        pdo_pgsql \
        pgsql \
        pcntl \
        zip \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && apk del .build-deps \
    && rm -rf /tmp/* /var/cache/apk/*

# Composer (última estable; versión se congela al build)
COPY --from=composer:2.7 /usr/bin/composer /usr/local/bin/composer

# Usuario non-root
RUN addgroup -g 1000 -S app \
    && adduser -u 1000 -S app -G app -h /home/app -s /bin/bash

# opcache config
COPY docker/php/opcache.ini /usr/local/etc/php/conf.d/zz-opcache.ini
COPY docker/php/php.ini /usr/local/etc/php/conf.d/zz-maestro.ini

WORKDIR /app

# ----- Stage dev -----
# Incluye xdebug, git, permite mount del código y hot reload via php-fpm
FROM base AS dev

# xdebug para desarrollo (deshabilitable via env XDEBUG_MODE)
RUN apk add --no-cache --virtual .xdebug-deps autoconf g++ make linux-headers \
    && pecl install xdebug \
    && docker-php-ext-enable xdebug \
    && apk del .xdebug-deps

COPY docker/php/xdebug.ini /usr/local/etc/php/conf.d/zz-xdebug.ini

# nginx como sidecar (en el mismo contenedor en dev para simplicidad)
RUN apk add --no-cache nginx supervisor \
    && mkdir -p /run/nginx /var/log/supervisor

COPY docker/php/nginx.conf /etc/nginx/nginx.conf
COPY docker/php/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/php/www.conf /usr/local/etc/php-fpm.d/zz-www.conf

# No crear ningún .env dentro de la imagen; se monta en runtime
USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD wget -q -O- http://127.0.0.1:8080/api/platform/health || exit 1

# En dev, supervisor arranca nginx + php-fpm
USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# ----- Stage prod -----
# Imagen slim sin xdebug, con code copiado en lugar de mount
FROM base AS prod

# Copia el código del repo (vendor ya pre-instalado por CI separado, o se puede
# hacer `composer install --no-dev --optimize-autoloader` acá)
COPY --chown=app:app backend /app

RUN composer install --no-dev --optimize-autoloader --no-interaction --no-progress \
    && php artisan config:cache \
    && php artisan route:cache \
    && php artisan view:cache

# nginx + supervisor igual que en dev
RUN apk add --no-cache nginx supervisor \
    && mkdir -p /run/nginx /var/log/supervisor

COPY docker/php/nginx.conf /etc/nginx/nginx.conf
COPY docker/php/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD wget -q -O- http://127.0.0.1:8080/api/platform/health || exit 1

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
