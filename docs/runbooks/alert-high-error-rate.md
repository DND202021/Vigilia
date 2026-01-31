# Alert: High Error Rate

## Overview

| Field | Value |
|-------|-------|
| Alert Name | HighErrorRate |
| Severity | Critical |
| Condition | Error rate > 5% for 5 minutes |
| RTO | 15 minutes |

## Description

This alert fires when the HTTP 5xx error rate exceeds 5% of total requests over a 5-minute window. High error rates indicate service degradation affecting users.

## Impact

- Users experience failed requests
- API consumers receive 5xx errors
- Real-time updates may fail
- Emergency responders may lose access to critical information

## Diagnosis

### 1. Check Current Error Rate

Open Grafana dashboard: **ERIOP API Performance**

Or query Prometheus directly:
```promql
sum(rate(http_requests_total{job="eriop-backend", status=~"5.."}[5m]))
/
sum(rate(http_requests_total{job="eriop-backend"}[5m]))
```

### 2. Identify Failing Endpoints

```promql
topk(10, sum(rate(http_requests_total{job="eriop-backend", status=~"5.."}[5m])) by (handler))
```

### 3. Check Backend Logs

```bash
# View recent errors
docker compose logs backend --since 10m | grep -i error

# Follow live logs
docker compose logs -f backend
```

### 4. Check Resource Usage

```bash
# Container stats
docker stats eriop-backend

# Memory usage
docker exec eriop-backend ps aux
```

### 5. Check Dependencies

```bash
# Database connectivity
docker exec eriop-backend python -c "from app.core.deps import engine; print('DB OK')"

# Redis connectivity
docker exec eriop-redis redis-cli ping
```

## Common Causes & Remediation

### Database Connection Pool Exhausted

**Symptoms:**
- Errors: "connection pool exhausted" or "QueuePool limit reached"
- Database connections maxed out

**Resolution:**
```bash
# Check current connections
docker exec eriop-db psql -U eriop -c "SELECT count(*) FROM pg_stat_activity WHERE datname='eriop';"

# Restart backend to reset connection pool
docker compose restart backend

# If persistent, increase pool size in environment:
# DATABASE_POOL_SIZE=20 (default is 5)
```

### Memory Exhaustion

**Symptoms:**
- OOMKilled containers
- Slow response times before errors

**Resolution:**
```bash
# Check memory usage
docker stats eriop-backend --no-stream

# Increase memory limit
# In docker-compose.prod.yml, update deploy.resources.limits.memory

# Restart with new limits
docker compose -f docker-compose.prod.yml up -d backend
```

### Dependency Failure (Database/Redis)

**Symptoms:**
- Connection refused errors
- Timeout errors

**Resolution:**
```bash
# Check dependency health
docker compose ps

# Restart failed service
docker compose restart postgres  # or redis

# Check logs
docker compose logs postgres --tail 50
```

### Application Bug / Regression

**Symptoms:**
- Errors in specific endpoints only
- Started after recent deployment

**Resolution:**
```bash
# Check recent deployments
git log --oneline -5

# Rollback to previous version
git checkout <previous-commit>
docker compose build backend
docker compose up -d backend
```

## Verification

After remediation, verify the fix:

1. **Check error rate is decreasing:**
   ```promql
   sum(rate(http_requests_total{job="eriop-backend", status=~"5.."}[1m]))
   ```

2. **Test critical endpoints:**
   ```bash
   curl -s http://localhost:8000/health
   curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
   ```

3. **Monitor for 10 minutes** to ensure stability

## Escalation

If unable to resolve within 15 minutes:

1. Notify on-call engineer
2. Consider enabling maintenance mode
3. Prepare for potential database failover

## Prevention

- Implement circuit breakers for external dependencies
- Set up database connection pool monitoring
- Configure memory limits appropriately
- Implement gradual rollouts for deployments

---
*Last reviewed: January 2025*
