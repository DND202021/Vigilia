# Phase 1: Foundation

**Timeline:** Weeks 1-4  
**Goal:** Establish core infrastructure and Fundamentum integration

## Overview

Phase 1 establishes the foundational architecture, development environment, and core services that all subsequent phases will build upon. This phase focuses on getting the basic infrastructure in place and achieving a working connection to the Fundamentum IoT Platform.

---

## Objectives

1. Set up project repository and CI/CD pipeline
2. Configure development environment
3. Establish Fundamentum integration layer (TALQ pattern)
4. Implement core authentication service (OAuth 2.0)
5. Build Role-Based Access Control (RBAC) framework
6. Design and implement database schema with migration system
7. Set up logging and audit infrastructure
8. Deploy basic API gateway

---

## Deliverables

### D1.1 Development Infrastructure

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| Repository | Git repository with branch protection | DevOps |
| CI/CD Pipeline | GitHub Actions for build, test, deploy | DevOps |
| Dev Environment | Docker Compose local setup | DevOps |
| Documentation | Contributing guide, setup instructions | Lead Dev |

**Acceptance Criteria:**
- [ ] Repository created with `main`, `develop`, `feature/*` branch strategy
- [ ] CI pipeline runs on all PRs (lint, test, security scan)
- [ ] CD pipeline deploys to staging on merge to `develop`
- [ ] Local dev environment starts with single command

### D1.2 Fundamentum Integration Layer

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| MQTT Client | Connection management with reconnection logic | Backend |
| Device Registry | Device registration and management | Backend |
| Telemetry Handler | Telemetry data ingestion pipeline | Backend |
| TALQ Adapter | TALQ-compliant message handling | Backend |

**Acceptance Criteria:**
- [ ] Successful MQTT connection to Fundamentum broker
- [ ] TLS secured connection
- [ ] Automatic reconnection with exponential backoff
- [ ] Device registration API functional
- [ ] Heartbeat/keepalive functional
- [ ] Telemetry messages received and processed

### D1.3 Authentication Service

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| OAuth 2.0 Server | Token issuance and validation | Backend |
| User Management | CRUD operations for users | Backend |
| MFA Support | TOTP-based MFA implementation | Backend |
| Session Management | JWT handling, refresh tokens | Backend |

**Acceptance Criteria:**
- [ ] Login endpoint returns JWT tokens
- [ ] Token refresh works correctly
- [ ] Logout invalidates sessions
- [ ] MFA challenge/verify flow works
- [ ] Password hashing uses bcrypt/Argon2
- [ ] Account lockout after 5 failed attempts

### D1.4 Authorization Framework

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| RBAC System | Role and permission management | Backend |
| Permission Guards | API endpoint protection | Backend |
| Agency Isolation | Multi-tenant data separation | Backend |

**Acceptance Criteria:**
- [ ] Roles can be created and assigned to users
- [ ] Permissions can be assigned to roles
- [ ] API endpoints enforce permission checks
- [ ] Users can only access their agency's data
- [ ] Authorization decisions are logged

### D1.5 Database Infrastructure

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| PostgreSQL Setup | Primary database with schema | Backend |
| TimescaleDB Setup | Time-series database for telemetry | Backend |
| Redis Setup | Cache and session store | Backend |
| Migrations | Alembic migration system | Backend |

**Acceptance Criteria:**
- [ ] Core tables created (users, agencies, roles, permissions)
- [ ] TimescaleDB hypertable for telemetry
- [ ] Redis connected for session/cache
- [ ] Migrations run without errors
- [ ] Rollback migrations work correctly

### D1.6 Logging and Audit

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| Structured Logging | JSON logging with correlation IDs | Backend |
| Audit Trail | Security event logging | Backend |
| Log Aggregation | Centralized logging setup | DevOps |

**Acceptance Criteria:**
- [ ] All API requests logged with request ID
- [ ] Authentication events logged
- [ ] Data modifications logged
- [ ] Logs are structured JSON
- [ ] No PII in logs

### D1.7 API Gateway

| Deliverable | Description | Owner |
|-------------|-------------|-------|
| Gateway Setup | NGINX/Kong configuration | DevOps |
| Rate Limiting | Per-user rate limits | DevOps |
| CORS Configuration | Secure CORS policy | DevOps |
| Health Checks | Endpoint health monitoring | Backend |

**Acceptance Criteria:**
- [ ] All API traffic routes through gateway
- [ ] Rate limiting functional
- [ ] CORS blocks unauthorized origins
- [ ] Health check endpoint returns status

---

## Technical Specifications

### Project Structure

```
eriop-project/
├── src/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI application
│   │   │   ├── config.py               # Configuration management
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── v1/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   │   ├── users.py        # User management
│   │   │   │   │   └── health.py       # Health checks
│   │   │   │   └── deps.py             # API dependencies
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── security.py         # JWT, password hashing
│   │   │   │   ├── rbac.py             # RBAC implementation
│   │   │   │   └── logging.py          # Structured logging
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── session.py          # Database session
│   │   │   │   └── base.py             # SQLAlchemy base
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── agency.py
│   │   │   │   ├── role.py
│   │   │   │   └── audit.py
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── auth.py
│   │   │   │   └── common.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   └── user.py
│   │   │   └── integrations/
│   │   │       ├── __init__.py
│   │   │       └── fundamentum/
│   │   │           ├── __init__.py
│   │   │           ├── client.py       # MQTT client
│   │   │           ├── telemetry.py    # Telemetry handler
│   │   │           └── registry.py     # Device registry
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   ├── requirements.txt
│   │   ├── requirements-dev.txt
│   │   └── pyproject.toml
│   └── frontend/                       # Placeholder for Phase 4
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   └── docker-compose.yml
│   ├── kubernetes/
│   │   └── base/
│   └── terraform/
├── scripts/
│   ├── setup-dev.sh
│   └── run-tests.sh
├── docs/
└── README.md
```

### Technology Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Type hints, asyncio |
| FastAPI | 0.109+ | Async web framework |
| SQLAlchemy | 2.0+ | ORM with async support |
| Alembic | 1.13+ | Database migrations |
| Pydantic | 2.5+ | Data validation |
| PostgreSQL | 15+ | Primary database |
| TimescaleDB | 2.x | Time-series extension |
| Redis | 7+ | Cache/sessions |
| paho-mqtt | 2.0+ | MQTT client |

### Environment Configuration

```python
# config.py structure
class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ERIOP"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: PostgresDsn
    TIMESCALE_URL: PostgresDsn
    REDIS_URL: RedisDsn
    
    # Fundamentum
    MQTT_BROKER_HOST: str
    MQTT_BROKER_PORT: int = 8883
    MQTT_USE_TLS: bool = True
    MQTT_CLIENT_ID: str
    MQTT_USERNAME: str
    MQTT_PASSWORD: SecretStr
    
    class Config:
        env_file = ".env"
```

---

## Success Criteria

| Criterion | Measure | Target |
|-----------|---------|--------|
| MQTT Connection | Connection established | Yes |
| JWT Authentication | Login/refresh works | Yes |
| Device Registration | Register device via API | Yes |
| Heartbeat | Device heartbeat received | Yes |
| Unit Test Coverage | Line coverage | > 80% |
| API Documentation | OpenAPI spec generated | Yes |
| Security Scan | No critical vulnerabilities | Yes |

---

## Dependencies

### External Dependencies
- Fundamentum API credentials
- Cloud infrastructure access
- SSL certificates for development

### Internal Dependencies
- Approved architecture design
- Security framework approval
- Database schema review

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Fundamentum API changes | Medium | High | Abstract integration layer, version pinning |
| Authentication complexity | Medium | Medium | Use proven libraries (authlib, python-jose) |
| Database schema changes | High | Medium | Robust migration strategy from start |

---

## Schedule

```
Week 1:
├── Day 1-2: Repository setup, CI/CD pipeline
├── Day 3-4: Development environment, Docker setup
└── Day 5: Database schema design

Week 2:
├── Day 1-2: PostgreSQL/TimescaleDB setup, migrations
├── Day 3-4: Authentication service basics
└── Day 5: MFA implementation

Week 3:
├── Day 1-2: RBAC framework
├── Day 3-4: Fundamentum MQTT client
└── Day 5: Device registry integration

Week 4:
├── Day 1-2: Telemetry pipeline
├── Day 3: API gateway setup
├── Day 4: Logging/audit infrastructure
└── Day 5: Testing, documentation, review
```

---

## Related Documents

- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design](../architecture/DATABASE_DESIGN.md)
- [Technical Requirements](../requirements/TECHNICAL_REQUIREMENTS.md)
- [Phase 2: Core Services](PHASE_02_CORE_SERVICES.md)

---

*Document Version: 1.0 | Last Updated: January 2025*
