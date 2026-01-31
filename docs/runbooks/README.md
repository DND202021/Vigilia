# ERIOP Operational Runbooks

This directory contains operational runbooks for responding to alerts and incidents in the ERIOP platform.

## Alert Runbooks

| Alert | Severity | Runbook |
|-------|----------|---------|
| HighErrorRate | Critical | [alert-high-error-rate.md](./alert-high-error-rate.md) |
| DatabasePoolExhausted | Critical | [alert-database-connection-pool.md](./alert-database-connection-pool.md) |
| RedisUnavailable | Critical | [alert-redis-unavailable.md](./alert-redis-unavailable.md) |
| HealthCheckFailing | Critical | [alert-health-check-failing.md](./alert-health-check-failing.md) |

## Disaster Recovery

- [disaster-recovery.md](./disaster-recovery.md) - Complete disaster recovery procedures

## Quick Reference

### Accessing Monitoring Tools

| Tool | URL | Default Credentials |
|------|-----|---------------------|
| Grafana | http://localhost:3003 | admin / admin |
| Prometheus | http://localhost:9090 | N/A |
| AlertManager | http://localhost:9093 | N/A |

### Common Commands

```bash
# Check container status
docker compose ps

# View backend logs
docker compose logs -f backend

# Restart backend
docker compose restart backend

# Check database connections
docker exec -it eriop-db psql -U eriop -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis status
docker exec -it eriop-redis redis-cli ping
```

### Escalation Contacts

Configure your team's escalation contacts in the AlertManager configuration:
`infrastructure/monitoring/alertmanager/alertmanager.yml`

## Updating Runbooks

When updating runbooks:
1. Keep procedures actionable and specific
2. Include exact commands to run
3. Document expected outputs
4. Keep recovery time objectives (RTO) in mind
5. Update the last-reviewed date
