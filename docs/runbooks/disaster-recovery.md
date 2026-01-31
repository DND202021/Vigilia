# Disaster Recovery Procedures

## Overview

This document outlines disaster recovery procedures for the ERIOP platform. Follow these procedures when normal recovery actions fail or when multiple critical systems are affected.

## Recovery Priority

| Priority | System | RTO | RPO |
|----------|--------|-----|-----|
| 1 | Backend API | 15 min | 0 |
| 2 | PostgreSQL Database | 30 min | 1 hour |
| 3 | Redis Cache | 15 min | Session data loss acceptable |
| 4 | Frontend | 30 min | 0 |
| 5 | Monitoring Stack | 1 hour | Metrics loss acceptable |

## Scenarios

### Complete Infrastructure Failure

**Symptoms:**
- All containers down
- Host machine unresponsive or crashed

**Recovery Steps:**

1. **Verify host machine status**
   ```bash
   ping <server-ip>
   ssh user@<server-ip>
   ```

2. **If host is up, check Docker**
   ```bash
   sudo systemctl status docker
   sudo systemctl restart docker
   ```

3. **Start all services**
   ```bash
   cd /path/to/Vigilia
   docker compose up -d
   ```

4. **Verify all services**
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

5. **Run database migrations if needed**
   ```bash
   docker exec eriop-backend alembic upgrade head
   ```

### Database Corruption or Loss

**Symptoms:**
- Database won't start
- Data corruption errors
- RDB/WAL corruption

**Recovery Steps:**

1. **Stop dependent services**
   ```bash
   docker compose stop backend
   ```

2. **Check database status**
   ```bash
   docker compose logs postgres --tail 100
   ```

3. **Attempt database recovery**
   ```bash
   docker compose stop postgres

   # If WAL corruption, try recovery mode
   docker exec eriop-db pg_resetwal /var/lib/postgresql/data

   docker compose start postgres
   ```

4. **If recovery fails, restore from backup**
   ```bash
   # Stop postgres
   docker compose stop postgres

   # Remove corrupted data
   docker volume rm eriop_postgres_data

   # Create new volume
   docker volume create eriop_postgres_data

   # Restore from backup
   docker compose up -d postgres
   docker exec -i eriop-db psql -U eriop < /backups/latest_backup.sql
   ```

5. **Restart backend**
   ```bash
   docker compose up -d backend
   docker exec eriop-backend alembic upgrade head
   ```

### Complete Data Loss (Backup Restore)

**Prerequisites:**
- Latest database backup available
- Application code at correct version

**Recovery Steps:**

1. **Stop all services**
   ```bash
   docker compose down
   ```

2. **Remove all volumes**
   ```bash
   docker volume rm $(docker volume ls -q | grep eriop)
   ```

3. **Recreate volumes**
   ```bash
   docker volume create eriop_postgres_data
   docker volume create eriop_redis_data
   docker volume create eriop_building_files
   ```

4. **Start database only**
   ```bash
   docker compose up -d postgres
   sleep 30  # Wait for initialization
   ```

5. **Restore database backup**
   ```bash
   # From SQL dump
   docker exec -i eriop-db psql -U eriop < /backups/eriop_backup_YYYYMMDD.sql

   # Or from pg_dump binary format
   docker exec -i eriop-db pg_restore -U eriop -d eriop < /backups/eriop_backup_YYYYMMDD.dump
   ```

6. **Restore file uploads**
   ```bash
   # Copy building files back
   docker cp /backups/building_files/. eriop-backend:/data/buildings/
   ```

7. **Start remaining services**
   ```bash
   docker compose up -d
   ```

8. **Verify restoration**
   ```bash
   curl http://localhost:8000/health/ready
   docker exec eriop-db psql -U eriop -c "SELECT count(*) FROM users;"
   ```

### Network Partition

**Symptoms:**
- Services can't communicate
- Connection refused between containers

**Recovery Steps:**

1. **Check Docker networks**
   ```bash
   docker network ls
   docker network inspect eriop-net
   ```

2. **Recreate network**
   ```bash
   docker compose down
   docker network rm eriop-net
   docker compose up -d
   ```

3. **If using external networks, reconnect**
   ```bash
   docker network connect eriop-net eriop-backend
   docker network connect eriop-net eriop-db
   ```

### Rollback to Previous Version

**When to use:**
- New deployment introduced bugs
- Critical functionality broken

**Recovery Steps:**

1. **Identify last working version**
   ```bash
   git log --oneline -10
   # Note the commit hash of last working version
   ```

2. **Checkout previous version**
   ```bash
   git checkout <commit-hash>
   ```

3. **Rebuild and deploy**
   ```bash
   docker compose build backend
   docker compose up -d backend
   ```

4. **Rollback database migrations if needed**
   ```bash
   # Check current migration
   docker exec eriop-backend alembic current

   # Downgrade to specific revision
   docker exec eriop-backend alembic downgrade <revision>
   ```

## Backup Procedures

### Database Backup

**Automated daily backup:**
```bash
#!/bin/bash
# backup-db.sh
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

docker exec eriop-db pg_dump -U eriop -Fc eriop > ${BACKUP_DIR}/eriop_${DATE}.dump

# Keep last 7 days
find ${BACKUP_DIR} -name "eriop_*.dump" -mtime +7 -delete
```

**Add to crontab:**
```bash
0 2 * * * /path/to/backup-db.sh
```

### File Storage Backup

```bash
#!/bin/bash
# backup-files.sh
BACKUP_DIR=/backups/files
DATE=$(date +%Y%m%d)

docker cp eriop-backend:/data/buildings ${BACKUP_DIR}/buildings_${DATE}

# Keep last 7 days
find ${BACKUP_DIR} -name "buildings_*" -mtime +7 -exec rm -rf {} \;
```

### Full System Backup

```bash
#!/bin/bash
# full-backup.sh
BACKUP_DIR=/backups/full
DATE=$(date +%Y%m%d)

# Stop services briefly
docker compose stop backend

# Backup all volumes
docker run --rm \
  -v eriop_postgres_data:/source/postgres:ro \
  -v eriop_redis_data:/source/redis:ro \
  -v eriop_building_files:/source/files:ro \
  -v ${BACKUP_DIR}:/backup \
  alpine tar -czvf /backup/eriop_full_${DATE}.tar.gz /source

# Restart services
docker compose start backend
```

## Monitoring Recovery

If the monitoring stack is down but application is running:

1. **Start monitoring services**
   ```bash
   docker compose up -d prometheus grafana alertmanager
   ```

2. **Verify Prometheus targets**
   - Open http://localhost:9090/targets
   - All targets should be "UP"

3. **Verify Grafana dashboards**
   - Open http://localhost:3003
   - Login with admin/admin
   - Check ERIOP dashboards

## Contact Information

| Role | Contact | Phone |
|------|---------|-------|
| On-Call Engineer | oncall@example.com | +1-XXX-XXX-XXXX |
| Database Admin | dba@example.com | +1-XXX-XXX-XXXX |
| DevOps Lead | devops@example.com | +1-XXX-XXX-XXXX |

## Post-Incident Actions

After recovering from an incident:

1. **Document the incident**
   - Timeline of events
   - Root cause analysis
   - Actions taken

2. **Update runbooks** if procedures were missing

3. **Improve monitoring** to catch issue earlier

4. **Review backup/restore** procedures

5. **Schedule post-mortem meeting**

---
*Last reviewed: January 2025*
