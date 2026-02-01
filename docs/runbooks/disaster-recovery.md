# Disaster Recovery Runbook

## Overview

This runbook covers recovery procedures for major system failures in the ERIOP platform.

## Backup Locations

| Data | Backup Method | Location | Frequency |
|------|--------------|----------|-----------|
| PostgreSQL | pg_dump | /backups/postgres/ | Daily |
| Redis | RDB snapshot | /backups/redis/ | Hourly |
| Building files | File sync | /backups/buildings/ | Continuous |
| Configuration | Git | GitHub repo | On change |

## Scenario 1: Database Corruption

### Recovery Steps

1. Stop the application
```bash
docker compose -f docker-compose.local.yml stop backend
```

2. Restore from backup
```bash
# Find latest backup
ls -la /backups/postgres/

# Restore
docker exec -i eriop-db psql -U eriop -d postgres -c "DROP DATABASE IF EXISTS eriop;"
docker exec -i eriop-db psql -U eriop -d postgres -c "CREATE DATABASE eriop;"
docker exec -i eriop-db psql -U eriop eriop < /backups/postgres/latest.sql
```

3. Run migrations
```bash
docker exec eriop-backend alembic upgrade head
```

4. Start application
```bash
docker compose -f docker-compose.local.yml start backend
```

## Scenario 2: Complete Server Failure

### Recovery Steps

1. Provision new server with Docker

2. Clone repository
```bash
git clone https://github.com/DND202021/Vigilia.git
cd Vigilia/Vigilia
```

3. Restore configuration
```bash
cp /backups/config/.env .env
```

4. Restore database backup
```bash
docker compose -f docker-compose.local.yml up -d db
# Wait for DB to be ready
docker exec -i eriop-db psql -U eriop eriop < /backups/postgres/latest.sql
```

5. Restore building files
```bash
cp -r /backups/buildings/* /data/buildings/
```

6. Start all services
```bash
docker compose -f docker-compose.local.yml up -d
```

7. Verify health
```bash
curl http://localhost:8000/health/ready
```

## Scenario 3: Ransomware/Security Breach

### Immediate Actions

1. **Isolate**: Disconnect from network
2. **Preserve**: Don't modify evidence
3. **Notify**: Alert security team
4. **Document**: Record timeline of events

### Recovery

1. Provision clean infrastructure
2. Restore from known-good backup (verify date)
3. Rotate all credentials:
   - Database passwords
   - JWT secret key
   - API keys
4. Review audit logs for breach scope
5. Implement additional security measures

## Testing Backups

Run monthly backup verification:

```bash
# Create test database
docker exec eriop-db createdb -U eriop eriop_test

# Restore backup
docker exec -i eriop-db psql -U eriop eriop_test < /backups/postgres/latest.sql

# Verify data
docker exec eriop-db psql -U eriop -d eriop_test -c "SELECT count(*) FROM users;"

# Cleanup
docker exec eriop-db dropdb -U eriop eriop_test
```

## Contact List

| Role | Contact |
|------|---------|
| Primary On-Call | [Configure in AlertManager] |
| Database Admin | [Configure] |
| Security Team | [Configure] |
