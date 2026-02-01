# Alert: Redis Unavailable

## Overview

- **Alert Name**: RedisUnavailable
- **Severity**: critical
- **Condition**: Redis ping fails for 2 minutes

## Symptoms

- Session/cache operations failing
- WebSocket connections dropping
- `/health/ready` shows redis as UNHEALTHY
- Increased API response times

## Investigation Steps

### 1. Check Redis Container

```bash
docker ps | grep redis
docker logs --tail 50 eriop-redis
```

### 2. Test Connectivity

```bash
docker exec eriop-redis redis-cli ping
```

### 3. Check Memory Usage

```bash
docker exec eriop-redis redis-cli info memory | grep -E "used_memory|maxmemory"
```

### 4. Check Client Connections

```bash
docker exec eriop-redis redis-cli info clients
```

### 5. Check for Blocked Operations

```bash
docker exec eriop-redis redis-cli slowlog get 10
```

## Resolution Actions

### Restart Redis Container

```bash
docker compose -f docker-compose.local.yml restart redis
```

### Clear All Data (last resort)

```bash
docker exec eriop-redis redis-cli FLUSHALL
```

### Check Disk Space

```bash
df -h /var/lib/docker
```

### Increase Memory Limit

Edit docker-compose to increase Redis memory limit:
```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Impact

When Redis is unavailable:
- User sessions may be lost
- Real-time features (WebSocket) will be degraded
- Caching will fall back to database (slower)

## Prevention

- Monitor Redis memory usage
- Set up Redis persistence (RDB/AOF)
- Configure maxmemory-policy appropriately
- Consider Redis Cluster for high availability
