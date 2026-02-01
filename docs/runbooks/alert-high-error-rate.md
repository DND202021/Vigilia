# Alert: High Error Rate

## Overview

- **Alert Name**: HighErrorRate
- **Severity**: critical
- **Condition**: HTTP 5xx error rate > 5% for 5 minutes

## Symptoms

- Users reporting errors or unable to access the application
- Increased latency in API responses
- Grafana shows spike in error rate on API dashboard

## Investigation Steps

### 1. Check Backend Logs

```bash
docker logs --tail 100 eriop-backend | grep -i error
```

Look for:
- Stack traces
- Database connection errors
- Redis connection errors
- Authentication failures

### 2. Check Health Endpoints

```bash
curl http://localhost:8000/health/ready
```

Review component status - identify unhealthy dependencies.

### 3. Check Database

```bash
# Connection count
docker exec eriop-db psql -U eriop -d eriop -c "SELECT count(*) FROM pg_stat_activity;"

# Long-running queries
docker exec eriop-db psql -U eriop -d eriop -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;"
```

### 4. Check Redis

```bash
docker exec eriop-redis redis-cli ping
docker exec eriop-redis redis-cli info stats | grep rejected
```

### 5. Check Resource Usage

```bash
docker stats --no-stream | grep eriop
```

## Resolution Actions

### Restart Backend (if unresponsive)

```bash
docker compose -f docker-compose.local.yml restart backend
```

### Clear Redis Cache (if corrupted)

```bash
docker exec eriop-redis redis-cli FLUSHDB
```

### Scale Backend (if overloaded)

```bash
docker compose -f docker-compose.local.yml up -d --scale backend=2
```

## Escalation

If the issue persists after 15 minutes:
1. Page on-call engineer
2. Check for upstream service issues
3. Consider rollback if recent deployment
