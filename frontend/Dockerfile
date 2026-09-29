# syntax=docker/dockerfile:1

# ---- build stage -----------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

# Dependencies first so this layer is cache-hit on every source-only change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- serve stage ------------------------------------------------------------
# No Node, no node_modules, no source in the final image — only the static
# build output and nginx.
FROM nginx:1.27-alpine AS serve

RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Run as non-root: nginx needs to own its runtime dirs and listen above 1024.
RUN addgroup -S webapp && adduser -S webapp -G webapp \
    && chown -R webapp:webapp /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx \
    && touch /var/run/nginx.pid \
    && chown webapp:webapp /var/run/nginx.pid

USER webapp
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
