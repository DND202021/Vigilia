# ERIOP Runbooks

Operational runbooks for responding to alerts and incidents in the ERIOP platform.

## Alert Runbooks

| Alert | Runbook | Severity |
|-------|---------|----------|
| HighErrorRate | [alert-high-error-rate.md](alert-high-error-rate.md) | critical |
| DatabasePoolExhausted | [alert-database-connection-pool.md](alert-database-connection-pool.md) | critical |
| RedisUnavailable | [alert-redis-unavailable.md](alert-redis-unavailable.md) | critical |
| HealthCheckFailing | [alert-health-check-failing.md](alert-health-check-failing.md) | critical |

## Other Runbooks

| Topic | Runbook |
|-------|---------|
| Disaster Recovery | [disaster-recovery.md](disaster-recovery.md) |

## Quick Reference

### Accessing Monitoring Tools

- **Grafana**: http://localhost:3003 (admin/admin on first login)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### Common Commands

```bash
# Check container status
docker ps | grep eriop

# View backend logs
docker logs -f eriop-backend

# Restart backend
docker compose -f docker-compose.local.yml restart backend

# Check database connections
docker exec eriop-db psql -U eriop -d eriop -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis
docker exec eriop-redis redis-cli ping
```

### Health Endpoints

- `/health` - Basic health check
- `/health/live` - Liveness probe (app is running)
- `/health/ready` - Readiness probe (all dependencies healthy)
- `/metrics` - Prometheus metrics
