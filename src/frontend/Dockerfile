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
RUN npm ci --only=production=false

# Copy source and build
COPY . .
RUN npm run build

# Production image
FROM nginx:alpine

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user
RUN adduser -D -u 101 -g nginx nginx-user && \
    chown -R nginx-user:nginx /var/cache/nginx && \
    chown -R nginx-user:nginx /var/log/nginx && \
    chown -R nginx-user:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx /var/run/nginx.pid

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

USER nginx-user

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
