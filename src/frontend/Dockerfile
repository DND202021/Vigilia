# ERIOP Frontend Production Dockerfile
# Multi-stage build for minimal production image

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Build arguments for API URLs
ARG VITE_API_URL=http://localhost:8000/api/v1
ARG VITE_WS_URL=ws://localhost:8000

# Set environment variables for build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source and build
COPY . .
# Skip TypeScript check in Docker (done during development)
RUN npx vite build

# Production image
FROM nginx:alpine

# Install envsubst for template processing
RUN apk add --no-cache gettext

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration template
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create startup script for Railway PORT handling
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'if [ -n "$PORT" ]; then' >> /docker-entrypoint.sh && \
    echo '  envsubst "\$PORT" < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf' >> /docker-entrypoint.sh && \
    echo 'fi' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Set default PORT
ENV PORT=80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:${PORT}/ || exit 1

EXPOSE 80

CMD ["/docker-entrypoint.sh"]
