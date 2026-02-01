# Alert: Database Connection Pool Exhausted

## Overview

- **Alert Name**: DatabasePoolExhausted
- **Severity**: critical
- **Condition**: Available database connections = 0

## Symptoms

- API requests timing out
- "Connection pool exhausted" errors in logs
- `/health/ready` shows db_pool as UNHEALTHY

## Investigation Steps

### 1. Check Pool Status

```bash
curl http://localhost:8000/health/ready | jq '.components[] | select(.name=="db_pool")'
```

### 2. Check Active Connections

```bash
docker exec eriop-db psql -U eriop -d eriop -c "
SELECT 
  state, 
  count(*) 
FROM pg_stat_activity 
WHERE datname = 'eriop' 
GROUP BY state;"
```

### 3. Find Long-Running Queries

```bash
docker exec eriop-db psql -U eriop -d eriop -c "
SELECT 
  pid, 
  now() - query_start AS duration, 
  state,
  LEFT(query, 100) as query
FROM pg_stat_activity 
WHERE datname = 'eriop' 
  AND state != 'idle'
ORDER BY duration DESC 
LIMIT 10;"
```

### 4. Check for Blocked Queries

```bash
docker exec eriop-db psql -U eriop -d eriop -c "
SELECT 
  blocked_locks.pid AS blocked_pid,
  blocking_locks.pid AS blocking_pid,
  blocked_activity.query AS blocked_query
FROM pg_locks blocked_locks
JOIN pg_stat_activity blocked_activity ON blocked_locks.pid = blocked_activity.pid
JOIN pg_locks blocking_locks ON blocked_locks.locktype = blocking_locks.locktype
  AND blocked_locks.relation = blocking_locks.relation
JOIN pg_stat_activity blocking_activity ON blocking_locks.pid = blocking_activity.pid
WHERE NOT blocked_locks.granted;"
```

## Resolution Actions

### Terminate Idle Connections

```bash
docker exec eriop-db psql -U eriop -d eriop -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'eriop' 
  AND state = 'idle' 
  AND query_start < now() - interval '10 minutes';"
```

### Kill Long-Running Queries

```bash
# Get PID from investigation, then:
docker exec eriop-db psql -U eriop -d eriop -c "SELECT pg_terminate_backend(PID_HERE);"
```

### Restart Backend

```bash
docker compose -f docker-compose.local.yml restart backend
```

### Increase Pool Size (temporary)

Edit docker-compose and increase `DATABASE_POOL_SIZE` env var, then restart.

## Prevention

- Review queries for N+1 patterns
- Add query timeouts
- Implement connection pooling at application level
- Monitor slow query logs
