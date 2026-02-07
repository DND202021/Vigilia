# Build stage: compile mosquitto-go-auth plugin
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache \
    git \
    mosquitto-dev \
    gcc \
    musl-dev \
    pkgconf

# Clone and build mosquitto-go-auth
WORKDIR /build
RUN git clone --depth 1 https://github.com/iegomez/mosquitto-go-auth.git . && \
    make

# Runtime stage: eclipse-mosquitto with the compiled plugin
FROM eclipse-mosquitto:2.0

# Copy the compiled auth plugin shared library
COPY --from=builder /build/go-auth.so /mosquitto/go-auth.so

# Default command (same as base image)
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
