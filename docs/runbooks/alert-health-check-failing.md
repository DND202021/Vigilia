# Alert: Health Check Failing

## Overview

| Field | Value |
|-------|-------|
| Alert Name | HealthCheckFailing |
| Severity | Critical |
| Condition | Backend /health endpoint fails for 2 minutes |
| RTO | 10 minutes |

## Description

This alert fires when the backend health check endpoint is not responding. This indicates the application is either down, unresponsive, or critically degraded.

## Impact

- Application is completely unavailable
- All API requests will fail
- Emergency responders cannot access the system
- WebSocket connections will drop

## Diagnosis

### 1. Check Backend Container

```bash
# Container status
docker compose ps backend

# Container logs
docker compose logs backend --tail 100

# Check if container is restarting
docker compose ps --format json | jq -r '.[] | select(.Service=="backend") | .State'
```

### 2. Test Health Endpoint

```bash
# Direct health check
curl -v http://localhost:8000/health

# Readiness check (includes dependencies)
curl -v http://localhost:8000/health/ready
```

### 3. Check Resource Usage

```bash
# Container stats
docker stats eriop-backend --no-stream

# Process inside container
docker exec eriop-backend ps aux
```

### 4. Check Dependencies

```bash
# Database
docker exec eriop-db pg_isready -U eriop

# Redis
docker exec eriop-redis redis-cli ping
```

### 5. Check Network

```bash
# Verify port is listening
docker exec eriop-backend netstat -tlnp | grep 8000

# Check from host
curl -s http://localhost:8001/health || echo "Failed"
```

## Common Causes & Remediation

### Application Crash

**Symptoms:**
- Container status: Exited or Restarting
- Error in logs

**Resolution:**
```bash
# Check crash reason
docker compose logs backend --tail 200

# Look for Python tracebacks
docker compose logs backend 2>&1 | grep -A 20 "Traceback"

# Restart
docker compose restart backend

# If persistent crash, check recent code changes
git log --oneline -5
```

### Memory Exhaustion (OOMKilled)

**Symptoms:**
- Container keeps restarting
- OOMKilled in inspect output

**Resolution:**
```bash
# Check if OOMKilled
docker inspect eriop-backend --format='{{.State.OOMKilled}}'

# Check memory limit
docker inspect eriop-backend --format='{{.HostConfig.Memory}}'

# Increase memory limit in docker-compose
# deploy:
#   resources:
#     limits:
#       memory: 2G

docker compose up -d backend
```

### Startup Failure

**Symptoms:**
- Container starts but health check never passes
- Import or initialization errors

**Resolution:**
```bash
# Check startup logs
docker compose logs backend 2>&1 | head -100

# Common issues:
# - Missing environment variables
# - Database migration needed
# - Port already in use

# Verify environment
docker exec eriop-backend env | grep -E "(DATABASE|REDIS|SECRET)"

# Run migrations if needed
docker exec eriop-backend alembic upgrade head
```

### Database Connection Failure

**Symptoms:**
- Health check fails but container running
- "Connection refused" to database

**Resolution:**
```bash
# Check database is running
docker compose ps postgres

# Restart database
docker compose restart postgres

# Wait for database to be ready
sleep 10

# Restart backend
docker compose restart backend
```

### Port Binding Conflict

**Symptoms:**
- Container won't start
- "Address already in use" error

**Resolution:**
```bash
# Find process using the port
sudo lsof -i :8000
sudo lsof -i :8001

# Kill conflicting process or change port
# Or restart Docker
docker compose down
docker compose up -d
```

## Immediate Recovery

```bash
# Quick restart
docker compose restart backend

# If that fails, full restart
docker compose down
docker compose up -d

# Nuclear option - full rebuild
docker compose down
docker compose build --no-cache backend
docker compose up -d
```

## Verification

1. **Health endpoint responding:**
   ```bash
   curl -s http://localhost:8000/health
   # Expected: {"status": "healthy", "version": "0.1.0"}
   ```

2. **Ready endpoint showing all components:**
   ```bash
   curl -s http://localhost:8000/health/ready | jq
   ```

3. **Prometheus target is up:**
   ```promql
   up{job="eriop-backend"} == 1
   ```

4. **Test actual functionality:**
   ```bash
   curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
   ```

## Health Check Configuration

The backend exposes multiple health endpoints:

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `/health` | Liveness | Application responding |
| `/health/live` | Kubernetes liveness | Same as /health |
| `/health/ready` | Readiness | DB, Redis, all services |

Docker health check configuration:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## Escalation

If unable to restore service within 10 minutes:

1. Notify on-call team
2. Check if rollback is needed
3. Consider failing over to backup instance
4. Activate incident response plan

---
*Last reviewed: January 2025*
