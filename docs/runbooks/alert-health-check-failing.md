# Alert: Health Check Failing

## Overview

- **Alert Name**: HealthCheckFailing
- **Severity**: critical
- **Condition**: Backend /health endpoint fails for 2 minutes

## Symptoms

- Application completely unavailable
- Load balancer removing backend from pool
- No API responses

## Investigation Steps

### 1. Check Container Status

```bash
docker ps -a | grep eriop-backend
```

If container is not running or restarting:
```bash
docker logs --tail 100 eriop-backend
```

### 2. Check Application Startup

Look for:
- Import errors
- Configuration issues
- Database migration failures
- Port binding conflicts

### 3. Check Resource Limits

```bash
docker stats --no-stream eriop-backend
```

### 4. Check Dependencies

```bash
# Database
docker exec eriop-db pg_isready -U eriop

# Redis
docker exec eriop-redis redis-cli ping
```

### 5. Try Manual Health Check

```bash
curl -v http://localhost:8000/health
curl -v http://localhost:8000/health/live
```

## Resolution Actions

### Restart Backend

```bash
docker compose -f docker-compose.local.yml restart backend
```

### Rebuild and Restart (if code issue)

```bash
docker compose -f docker-compose.local.yml build backend
docker compose -f docker-compose.local.yml up -d backend
```

### Check and Apply Migrations

```bash
docker exec eriop-backend alembic upgrade head
```

### Force Recreate Container

```bash
docker compose -f docker-compose.local.yml up -d --force-recreate backend
```

## Common Causes

1. **Out of Memory**: Container killed by OOM
2. **Unhandled Exception**: Application crash on startup
3. **Database Unavailable**: Can't connect during startup
4. **Port Conflict**: Another process using port 8000
5. **Bad Configuration**: Missing or invalid environment variables

## Escalation

If backend won't start after restart:
1. Check recent code changes
2. Review deployment logs
3. Consider rollback to last known good version
