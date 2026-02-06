# Load Test Report - ERIOP Backend

**Date:** 2026-02-06
**Plan:** 15-06
**Status:** PENDING EXECUTION
**Environment:** Docker environment required

## Executive Summary

Load testing infrastructure has been created and validated for the ERIOP backend. The test suite is ready for execution in a Docker environment to validate performance targets:

- **1000 alerts/sec** throughput
- **10,000 concurrent** API requests
- **p95 latency < 200ms**

## Test Infrastructure

### Locust Test Suite
- **File:** `loadtest/locustfile.py`
- **Validation:** ✅ Syntax validated with `py_compile`
- **User Personas:** 3 types with realistic behavior patterns
  - ERIOPDispatcher (30% weight)
  - ERIOPResponder (50% weight)
  - AlertIngestion (20% weight)

### Data Seeding
- **File:** `loadtest/seed_data.py`
- **Test Data:**
  - 1 test agency
  - 350 test users (100 dispatchers, 200 responders, 50 alert systems)
  - 50 buildings
  - 100 resources
  - 50 baseline incidents
  - 100 baseline alerts

### Docker Configuration
- **File:** `docker-compose.loadtest.yml`
- **Architecture:** Distributed load generation
  - 1 Locust master (Web UI on port 8089)
  - 4 Locust workers
  - Connected to `vigilia_default` network
- **Validation:** ✅ YAML syntax valid

## Test Scenarios

### Scenario 1: Baseline Performance
**Objective:** Establish performance baseline with moderate load

**Configuration:**
- Users: 1,000
- Spawn rate: 50 users/sec
- Duration: 5 minutes
- Endpoint coverage: All major APIs

**Expected Metrics:**
- Request rate: 200-500 RPS
- p95 response time: < 100ms
- Failure rate: < 0.1%

### Scenario 2: Alert Throughput Test
**Objective:** Validate 1000 alerts/sec ingestion

**Configuration:**
- Users: 2,000 (AlertIngestion class only)
- Spawn rate: 100 users/sec
- Duration: 5 minutes
- Endpoint: POST /api/v1/alerts/ingest

**Expected Metrics:**
- Alert ingestion rate: > 1000/sec
- p95 response time: < 200ms
- Zero alert loss

### Scenario 3: Concurrent Request Load
**Objective:** Validate 10k concurrent requests

**Configuration:**
- Users: 10,000 (all personas)
- Spawn rate: 100 users/sec
- Duration: 10 minutes
- Endpoint coverage: All APIs with realistic ratios

**Expected Metrics:**
- Sustained concurrent users: 10,000
- p95 response time: < 200ms
- p99 response time: < 500ms
- Failure rate: < 1%

### Scenario 4: Stress Test
**Objective:** Find system breaking point

**Configuration:**
- Users: Start at 10,000, increase by 1,000 every 2 minutes
- Spawn rate: 200 users/sec
- Duration: Until failure or 20,000 users
- Endpoint coverage: All APIs

**Expected Metrics:**
- Identify maximum sustained load
- Document degradation patterns
- Capture failure modes

## Execution Instructions

### Prerequisites
1. Docker and Docker Compose installed
2. ERIOP stack running (`docker compose up -d`)
3. At least 8GB RAM allocated to Docker
4. Network bandwidth: 100 Mbps+

### Step-by-Step Execution

#### 1. Seed Test Data
```bash
cd /workspace/Vigilia/Vigilia
docker compose exec backend python /app/../loadtest/seed_data.py
```

Expected output:
```
ERIOP Load Test Data Seeding
============================
Creating test agency...
Creating test users...
Creating 100 dispatchers...
Creating 200 responders...
Creating 50 alert system users...
Creating 50 test buildings...
Creating 100 test resources...
Creating 50 baseline incidents...
Creating 100 baseline alerts...

Seeding Complete!
============================
Created:
  - 1 test agency
  - 100 dispatchers
  - 200 responders
  - 50 alert system users
  - 50 buildings
  - 100 resources
  - 50 incidents
  - 100 alerts
============================
```

#### 2. Start Locust Cluster
```bash
docker compose -f docker-compose.loadtest.yml up -d
```

Verify all containers running:
```bash
docker compose -f docker-compose.loadtest.yml ps
```

Expected:
```
NAME                    STATUS
eriop-locust-master     Up
eriop-locust-worker-1   Up
eriop-locust-worker-2   Up
eriop-locust-worker-3   Up
eriop-locust-worker-4   Up
```

#### 3. Access Locust Web UI
Open http://localhost:8089

#### 4. Run Scenario 1 (Baseline)
- Number of users: 1000
- Spawn rate: 50
- Host: http://backend:8000
- Click "Start swarming"
- Run for 5 minutes
- Download CSV and HTML reports

#### 5. Run Scenario 2 (Alert Throughput)
- Stop previous test
- Number of users: 2000
- Spawn rate: 100
- Host: http://backend:8000
- User class filter: AlertIngestion
- Click "Start swarming"
- Run for 5 minutes
- Download reports

#### 6. Run Scenario 3 (Concurrent Load)
- Stop previous test
- Number of users: 10000
- Spawn rate: 100
- Host: http://backend:8000
- Click "Start swarming"
- Run for 10 minutes
- Download reports

#### 7. Run Scenario 4 (Stress Test)
- Stop previous test
- Number of users: 10000
- Spawn rate: 200
- Host: http://backend:8000
- Click "Start swarming"
- Monitor metrics
- Manually increase user count by 1000 every 2 minutes
- Stop when failure rate > 5% or response times degrade
- Download reports

### Headless Execution (CI/CD)

For automated testing without Web UI:

```bash
# Scenario 3 (10k concurrent)
docker compose -f docker-compose.loadtest.yml run --rm locust-master \
  -f /mnt/locust/locustfile.py \
  --headless \
  --users 10000 \
  --spawn-rate 100 \
  --run-time 10m \
  --host http://backend:8000 \
  --html /mnt/locust/report.html \
  --csv /mnt/locust/results \
  --csv-full-history

# Results saved to:
# - loadtest/report.html
# - loadtest/results_stats.csv
# - loadtest/results_stats_history.csv
# - loadtest/results_failures.csv
```

## Results Format

### Required Metrics

After execution, update this section with actual results:

#### Scenario 1: Baseline Performance
```
Status: PENDING
Duration: -
Total Requests: -
Failure Rate: -
Requests/sec: -
Response Times:
  - p50: -
  - p95: -
  - p99: -
  - Max: -
```

#### Scenario 2: Alert Throughput
```
Status: PENDING
Duration: -
Total Alerts: -
Alerts/sec: -
Failure Rate: -
Response Times:
  - p50: -
  - p95: -
  - p99: -
```

#### Scenario 3: Concurrent Request Load
```
Status: PENDING
Duration: -
Peak Concurrent Users: -
Total Requests: -
Failure Rate: -
Requests/sec: -
Response Times:
  - p50: -
  - p95: -
  - p99: -
  - Max: -
```

#### Scenario 4: Stress Test
```
Status: PENDING
Max Sustained Users: -
Breaking Point: -
Failure Mode: -
Response Times at Peak:
  - p50: -
  - p95: -
  - p99: -
```

### Endpoint Breakdown

Update with actual data from CSV reports:

| Endpoint | Requests | Failures | Avg (ms) | p95 (ms) | p99 (ms) | RPS |
|----------|----------|----------|----------|----------|----------|-----|
| GET /incidents/active | - | - | - | - | - | - |
| GET /alerts/pending | - | - | - | - | - | - |
| GET /resources/available | - | - | - | - | - | - |
| POST /incidents | - | - | - | - | - | - |
| POST /alerts/ingest | - | - | - | - | - | - |
| GET /auth/me | - | - | - | - | - | - |

## Analysis Template

### Performance vs Targets

Once executed, analyze:

**✅/❌ Alert Throughput Target (1000/sec)**
- Achieved: TBD
- Notes: TBD

**✅/❌ Concurrent Requests Target (10k)**
- Achieved: TBD
- Notes: TBD

**✅/❌ Response Time Target (p95 < 200ms)**
- Achieved: TBD
- Notes: TBD

### Bottleneck Identification

Look for:
- Database query performance (check slow query logs)
- Connection pool exhaustion (monitor pool metrics)
- CPU/memory saturation (docker stats)
- Network bandwidth limits
- Redis cache hit rate

### Scalability Assessment

Document:
- Linear scaling up to X users
- Degradation begins at Y users
- Hard limit at Z users
- Resource constraints (CPU, memory, I/O)

### Recommendations

Based on results, recommend:
- Database optimizations (indexes, query tuning)
- Backend scaling (worker count, resource limits)
- Caching strategy improvements
- Infrastructure upgrades

## Infrastructure Metrics

### Backend Container

Monitor during tests:
```bash
docker stats eriop-backend
```

Expected metrics:
- CPU: < 80% average
- Memory: < 2GB
- Network I/O: Monitor for bandwidth saturation

### Database Container

Monitor during tests:
```bash
docker stats eriop-db

# Active connections
docker compose exec db psql -U eriop -c "
  SELECT count(*) as active_connections
  FROM pg_stat_activity
  WHERE state = 'active';"

# Slow queries
docker compose exec db psql -U eriop -c "
  SELECT query, calls, mean_exec_time, max_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;"
```

### Redis Container

Monitor during tests:
```bash
docker stats eriop-redis

# Cache stats
docker compose exec redis redis-cli INFO stats
docker compose exec redis redis-cli INFO memory
```

## Cleanup

After testing, remove test data:

```bash
# SQL cleanup
docker compose exec db psql -U eriop <<EOF
DELETE FROM users WHERE email LIKE '%@test.eriop.local';
DELETE FROM agencies WHERE agency_code = 'LOADTEST';
-- Cascading deletes remove related records
EOF

# Or full reset
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
```

Stop Locust cluster:
```bash
docker compose -f docker-compose.loadtest.yml down
```

## Appendix: Known Limitations

### Alert Ingestion Endpoint
The load test references `POST /api/v1/alerts/ingest` which may need to be implemented. Currently, alerts are created through integration services. For load testing, consider:

1. **Option A:** Create dedicated ingestion endpoint with minimal validation
2. **Option B:** Use existing incident creation as proxy for write throughput
3. **Option C:** Mock the alert ingestion layer

### Authentication Rate Limiting
If rate limiting is enabled, dispatchers/responders may encounter 429 errors. Consider:
- Disabling rate limits during load tests
- Or increasing limits to realistic values
- Or distributing load across more test users

### Database Connection Pooling
Default pool size may be insufficient for 10k users. Adjust in `docker-compose.yml`:
```yaml
environment:
  - PGBOUNCER_MAX_CLIENT_CONN=10000
  - PGBOUNCER_DEFAULT_POOL_SIZE=100
```

## Next Steps

1. **Execute tests** in Docker environment
2. **Capture results** and update this report
3. **Analyze bottlenecks** and document findings
4. **Implement optimizations** based on results
5. **Re-test** to validate improvements
6. **Archive results** for regression testing

---

**Report Status:** PENDING EXECUTION
**Created:** 2026-02-06
**Author:** Claude (Plan 15-06)
**Next Action:** Execute in Docker environment and update with actual results
