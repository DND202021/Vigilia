# ERIOP Load Testing with Locust

This directory contains load test infrastructure for validating ERIOP's performance targets:

- **1000 alerts/sec** throughput
- **10,000 concurrent** API requests
- **p95 latency < 200ms**

## Components

### `locustfile.py`
Main test suite with 3 user personas:

1. **ERIOPDispatcher (30% weight)** - Active users creating incidents, acknowledging alerts
2. **ERIOPResponder (50% weight)** - Field users primarily reading data
3. **AlertIngestion (20% weight)** - High-frequency alert posting for throughput testing

### `seed_data.py`
Database seeding script that creates:
- 1 test agency
- 350 test users (100 dispatchers, 200 responders, 50 alert systems)
- 50 buildings
- 100 resources (40 personnel, 40 vehicles, 20 equipment)
- 50 baseline incidents
- 100 baseline alerts

### `docker-compose.loadtest.yml`
Locust cluster configuration:
- 1 master node (Web UI on port 8089)
- 4 worker nodes for distributed load generation
- Connected to `vigilia_default` network

## Quick Start

### 1. Ensure main stack is running
```bash
docker compose up -d
```

### 2. Seed test data
```bash
docker compose exec backend python /app/../loadtest/seed_data.py
```

### 3. Start Locust cluster
```bash
docker compose -f docker-compose.loadtest.yml up -d
```

### 4. Access Web UI
Open http://localhost:8089

Configure test:
- **Number of users**: 10000
- **Spawn rate**: 100 users/sec
- **Host**: http://backend:8000

### 5. Monitor results
Watch real-time metrics in Web UI:
- Request rate (RPS)
- Response times (p50, p95, p99)
- Failure rate
- Active users

### 6. Stop test
Click "Stop" in Web UI or:
```bash
docker compose -f docker-compose.loadtest.yml down
```

## Headless Mode (CI/CD)

Run tests without Web UI:

```bash
docker compose -f docker-compose.loadtest.yml run --rm locust-master \
  -f /mnt/locust/locustfile.py \
  --headless \
  --users 10000 \
  --spawn-rate 100 \
  --run-time 5m \
  --host http://backend:8000 \
  --html /mnt/locust/report.html \
  --csv /mnt/locust/results
```

Results saved to:
- `loadtest/report.html` - HTML report
- `loadtest/results_stats.csv` - Request statistics
- `loadtest/results_stats_history.csv` - Time-series data
- `loadtest/results_failures.csv` - Failure log

## Performance Targets

### Alert Throughput
Target: 1000 alerts/sec

Test configuration:
- AlertIngestion users: 2000 (20% of 10k)
- Wait time: 0.1-0.5 seconds
- Expected RPS: 1000-2000 alerts/sec

### Concurrent Requests
Target: 10,000 concurrent requests

Test configuration:
- Total users: 10,000
- All user types active simultaneously
- Average response time < 200ms

### Response Time
Target: p95 < 200ms

Monitor in Locust UI:
- Check "Response Times (ms)" chart
- Verify 95th percentile stays below 200ms
- Watch for degradation as user count increases

## Interpreting Results

### Success Criteria
- ✅ Request failure rate < 1%
- ✅ p95 response time < 200ms
- ✅ Alert ingestion rate > 1000/sec
- ✅ 10,000 users sustained for 5+ minutes

### Common Issues

**High Failure Rate**
- Database connection pool exhausted
- Backend worker count too low
- Network bandwidth saturation

**High Response Times**
- Database query performance (missing indexes)
- Synchronous I/O blocking workers
- CPU/memory resource limits

**Low Throughput**
- Worker count insufficient
- Database write bottleneck
- Redis cache misses

## Cleanup

Remove test data:
```sql
DELETE FROM users WHERE email LIKE '%@test.eriop.local';
DELETE FROM agencies WHERE agency_code = 'LOADTEST';
-- Cascading deletes will remove related records
```

Or reset entire database:
```bash
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
```

## Advanced Usage

### Custom Test Scenarios

Edit `locustfile.py` to adjust:
- Task weights (change `@task(N)` values)
- Wait times (`wait_time = between(min, max)`)
- User class weights (`weight = N`)

### Targeting Specific Endpoints

Run single user class:
```bash
docker compose -f docker-compose.loadtest.yml run --rm locust-master \
  -f /mnt/locust/locustfile.py \
  --headless \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 2m \
  --host http://backend:8000 \
  ERIOPDispatcher  # Only run this user class
```

### Distributed Load Generation

Scale workers horizontally:
```bash
docker compose -f docker-compose.loadtest.yml up -d --scale locust-worker=10
```

## Monitoring Backend

Watch backend performance:
```bash
# Backend logs
docker compose logs -f backend

# Database connections
docker compose exec db psql -U eriop -c "SELECT count(*) FROM pg_stat_activity;"

# Redis stats
docker compose exec redis redis-cli INFO stats

# Container resources
docker stats
```

## Troubleshooting

### Workers not connecting
```bash
# Check network
docker network inspect vigilia_default

# Check master logs
docker logs eriop-locust-master

# Restart workers
docker compose -f docker-compose.loadtest.yml restart
```

### Out of memory
Reduce user count or increase Docker memory limit:
```bash
docker compose -f docker-compose.loadtest.yml down
# Edit Docker Desktop settings to increase memory
docker compose -f docker-compose.loadtest.yml up -d
```

### Database locked
PostgreSQL connection limit reached:
```bash
# Increase max_connections in docker-compose.yml
# Or reduce Locust user count
```
