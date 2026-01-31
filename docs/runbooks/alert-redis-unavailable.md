# Alert: Redis Unavailable

## Overview

| Field | Value |
|-------|-------|
| Alert Name | RedisUnavailable |
| Severity | Critical |
| Condition | Redis not responding to ping |
| RTO | 10 minutes |

## Description

This alert fires when the Redis server is not responding or the backend cannot connect to Redis. Redis is used for caching, session management, and real-time pub/sub.

## Impact

- Session management may fail
- Real-time WebSocket events will not propagate
- Caching disabled, increased database load
- Rate limiting may not work correctly

## Diagnosis

### 1. Check Redis Container Status

```bash
# Check if Redis is running
docker compose ps redis

# Check Redis logs
docker compose logs redis --tail 50
```

### 2. Test Redis Connectivity

```bash
# From host
docker exec eriop-redis redis-cli ping

# With authentication (if configured)
docker exec eriop-redis redis-cli -a "${REDIS_PASSWORD}" ping
```

### 3. Check Backend Connection

```promql
eriop_redis_connected
```

```bash
# Check backend logs for Redis errors
docker compose logs backend --since 5m | grep -i redis
```

### 4. Check Redis Memory

```bash
docker exec eriop-redis redis-cli info memory
```

### 5. Check System Resources

```bash
# Container resource usage
docker stats eriop-redis --no-stream

# Disk space (Redis persistence)
df -h
```

## Common Causes & Remediation

### Redis Container Crashed

**Symptoms:**
- Container status: Exited or Restarting
- OOMKilled in logs

**Resolution:**
```bash
# Check exit reason
docker inspect eriop-redis --format='{{.State.OOMKilled}}'
docker compose logs redis --tail 100

# Restart Redis
docker compose up -d redis

# If OOMKilled, increase memory limit in docker-compose
```

### Memory Exhaustion

**Symptoms:**
- OOMKilled or memory warnings in logs
- Redis maxmemory reached

**Resolution:**
```bash
# Check current memory usage
docker exec eriop-redis redis-cli info memory | grep used_memory_human

# Clear expired keys
docker exec eriop-redis redis-cli --scan --pattern "*" | head -1000

# If using maxmemory policy, it should auto-evict
# Verify policy:
docker exec eriop-redis redis-cli config get maxmemory-policy

# Restart with more memory
# Update docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 512M
docker compose up -d redis
```

### Network Connectivity Issues

**Symptoms:**
- Redis running but backend can't connect
- "Connection refused" or timeout errors

**Resolution:**
```bash
# Check Docker network
docker network inspect eriop-internal

# Verify Redis is listening
docker exec eriop-redis netstat -tlnp

# Test from backend container
docker exec eriop-backend python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"
```

### Authentication Failure

**Symptoms:**
- "NOAUTH Authentication required" errors
- Password mismatch

**Resolution:**
```bash
# Verify password in docker-compose matches backend config
grep REDIS_PASSWORD docker-compose*.yml

# Test with password
docker exec eriop-redis redis-cli -a "your_password" ping

# If password was changed, restart backend
docker compose restart backend
```

### Persistence Issues

**Symptoms:**
- Redis crashes on startup
- AOF or RDB file corruption

**Resolution:**
```bash
# Check persistence status
docker exec eriop-redis redis-cli info persistence

# If AOF is corrupted, repair it
docker exec eriop-redis redis-check-aof --fix /data/appendonly.aof

# If RDB is corrupted, remove and restart
# WARNING: This loses cached data
docker compose stop redis
docker volume rm eriop_redis_data
docker compose up -d redis
```

## Immediate Recovery

```bash
# Quick restart
docker compose restart redis

# If restart fails, recreate
docker compose stop redis
docker compose rm redis
docker compose up -d redis

# Restart backend to reconnect
docker compose restart backend
```

## Verification

1. **Check Redis responding:**
   ```bash
   docker exec eriop-redis redis-cli ping
   # Expected: PONG
   ```

2. **Check backend connection:**
   ```promql
   eriop_redis_connected == 1
   ```

3. **Test WebSocket functionality:**
   - Open application in browser
   - Check real-time updates are working

## Fallback Behavior

The application should degrade gracefully when Redis is unavailable:
- Caching: Falls back to direct database queries
- Sessions: May require re-authentication
- Real-time: Socket.IO falls back to polling

## Prevention

- Set appropriate maxmemory limits
- Configure maxmemory-policy (e.g., allkeys-lru)
- Monitor memory usage with alerts at 80%
- Regular backup of RDB snapshots
- Use Redis Sentinel for high availability (production)

---
*Last reviewed: January 2025*
