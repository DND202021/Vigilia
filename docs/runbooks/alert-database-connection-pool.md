# Alert: Database Connection Pool Exhausted

## Overview

| Field | Value |
|-------|-------|
| Alert Name | DatabasePoolExhausted |
| Severity | Critical |
| Condition | Available connections = 0 |
| RTO | 10 minutes |

## Description

This alert fires when the SQLAlchemy connection pool has no available connections. All new database operations will block or fail until connections are released.

## Impact

- All database operations fail or timeout
- API requests return 500 errors
- Real-time features stop working
- Emergency responders lose access to incident data

## Diagnosis

### 1. Check Pool Metrics

```promql
eriop_db_pool_available
```

### 2. Check Database Connections

```bash
# Total connections to eriop database
docker exec eriop-db psql -U eriop -c "
SELECT count(*), state
FROM pg_stat_activity
WHERE datname='eriop'
GROUP BY state;
"

# Long-running queries (potential connection holders)
docker exec eriop-db psql -U eriop -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE datname = 'eriop'
  AND state != 'idle'
  AND now() - pg_stat_activity.query_start > interval '30 seconds'
ORDER BY duration DESC;
"
```

### 3. Check for Blocked Queries

```bash
docker exec eriop-db psql -U eriop -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

### 4. Check Backend Logs

```bash
docker compose logs backend --since 5m | grep -i "pool\|connection\|timeout"
```

## Common Causes & Remediation

### Connection Leak

**Symptoms:**
- Pool exhaustion without high traffic
- Gradual increase in connections over time

**Resolution:**
```bash
# Restart backend to release all connections
docker compose restart backend

# Check code for:
# - Missing async with statements for sessions
# - Exceptions not properly closing connections
# - Long-running transactions
```

### Long-Running Queries

**Symptoms:**
- Active queries holding connections
- Specific operations taking too long

**Resolution:**
```bash
# Identify and kill long-running queries
docker exec eriop-db psql -U eriop -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'eriop'
  AND state = 'active'
  AND now() - query_start > interval '5 minutes';
"
```

### Traffic Spike

**Symptoms:**
- Sudden increase in concurrent users
- High request rate in metrics

**Resolution:**
```bash
# Increase pool size (temporary)
# Add to docker-compose environment:
# DATABASE_POOL_SIZE=20

# Restart backend
docker compose restart backend
```

### Database Lock Contention

**Symptoms:**
- Blocked queries visible
- Specific tables locked

**Resolution:**
```bash
# Identify blocking queries and terminate them
docker exec eriop-db psql -U eriop -c "
SELECT pg_terminate_backend(blocking_pid)
FROM (
  SELECT blocking_locks.pid AS blocking_pid
  FROM pg_catalog.pg_locks blocked_locks
  JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.pid != blocked_locks.pid
    AND blocking_locks.locktype = blocked_locks.locktype
  WHERE NOT blocked_locks.granted
) AS blockers;
"
```

## Immediate Recovery

If diagnosis is taking too long:

```bash
# Quick recovery - restart backend
docker compose restart backend

# If that fails, restart database and backend
docker compose restart postgres
sleep 10
docker compose restart backend
```

## Verification

1. **Check pool availability:**
   ```promql
   eriop_db_pool_available > 0
   ```

2. **Check active connections are reasonable:**
   ```bash
   docker exec eriop-db psql -U eriop -c "SELECT count(*) FROM pg_stat_activity WHERE datname='eriop';"
   ```

3. **Test API functionality:**
   ```bash
   curl -s http://localhost:8000/health/ready | jq
   ```

## Prevention

- Monitor pool metrics with alerts at 80% usage
- Set query timeouts: `statement_timeout = 30s`
- Use connection pool overflow: `pool_pre_ping=True`
- Implement request timeouts at application level
- Regular analysis of slow queries

## Configuration Reference

Default pool settings in SQLAlchemy:
```python
# app/core/deps.py
create_async_engine(
    settings.database_url,
    pool_size=5,        # Default connections
    max_overflow=10,    # Extra connections allowed
    pool_timeout=30,    # Wait time for connection
    pool_pre_ping=True, # Check connection health
)
```

---
*Last reviewed: January 2025*
