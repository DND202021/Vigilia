# CLAUDE.md - Context for Claude Code

This file provides context for Claude Code when working on this project.

## Project Overview

**Project:** ERIOP (Emergency Response IoT Platform)
**Repository:** https://github.com/DND202021/Vigilia
**Division:** Vigilia (Security Division)

ERIOP is a mission-critical platform designed to provide real-time tactical and strategic information to emergency responders (SWAT, police, firefighters, medics). Built on the Fundamentum IoT Platform by Amotus.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Database | PostgreSQL + TimescaleDB |
| Cache | Redis |
| Frontend | React + TypeScript + Vite |
| Mobile | React Native (planned) |
| Infrastructure | Docker + Kubernetes |
| IoT Platform | Fundamentum (Amotus) |

## Project Structure

```
Vigilia/
├── src/
│   ├── backend/          # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/      # REST endpoints
│   │   │   ├── core/     # Config, security, deps
│   │   │   ├── models/   # SQLAlchemy models
│   │   │   ├── services/ # Business logic
│   │   │   └── integrations/  # External systems
│   │   ├── alembic/      # Database migrations
│   │   └── tests/        # Pytest tests (176 tests)
│   └── frontend/         # React web app
│       ├── src/
│       │   ├── components/   # UI components
│       │   ├── pages/        # Route pages
│       │   ├── stores/       # Zustand state
│       │   ├── services/     # API & offline
│       │   └── hooks/        # Custom hooks
│       └── public/           # Static assets
├── docs/
│   ├── architecture/     # System design
│   ├── phases/           # Development phases
│   └── requirements/     # Specs
└── infrastructure/       # Docker + K8s configs
    ├── nginx/            # Reverse proxy config
    └── k8s/              # Kubernetes manifests
```

## Development Progress

### Completed

- [x] **Phase 1: Foundation** (January 2025)
  - SQLAlchemy models (User, Agency, Incident, Resource, Alert)
  - JWT authentication service
  - Alembic migrations
  - Unit tests (33 tests passing)

- [x] **Phase 2: Core Services**
  - Incident management service
  - Resource tracking service
  - Alert processing service
  - Unit tests (50+ tests)

- [x] **Phase 3: Integrations**
  - Circuit breaker pattern for fault tolerance
  - Alarm system integration (Contact ID protocol)
  - Axis audio analytics integration
  - CAD system adapter with sync service
  - GIS service (geocoding, routing, jurisdictions)
  - Unit tests (93 tests)

- [x] **Phase 4: User Interfaces**
  - React + TypeScript frontend
  - Dashboard with real-time data
  - Incidents list and detail pages
  - Alerts management page
  - Resources tracking page
  - Tactical map with Leaflet
  - Authentication flow (login/logout)
  - Zustand state management
  - API client with token refresh

- [x] **Phase 5: Offline Capability**
  - Service Worker for caching
  - IndexedDB offline storage
  - Sync service for background sync
  - Offline status indicator
  - PWA manifest

- [x] **Phase 6: Security Hardening**
  - Input validation and sanitization
  - XSS prevention (HTML escaping)
  - Rate limiting
  - Content Security Policy
  - Secure storage wrapper
  - Session timeout management

- [x] **Phase 7: Testing & Certification**
  - Backend: 176 pytest tests
  - Frontend: Vitest unit tests
  - Validation tests
  - Store tests

- [x] **Phase 8: Production Deployment**
  - Docker multi-stage builds
  - Docker Compose (dev + prod)
  - Kubernetes manifests
  - Nginx reverse proxy config
  - SSL/TLS configuration
  - Health checks
  - Resource limits

## Key Commands

### Backend Development
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v                    # Run tests (176 passing)
uvicorn app.main:app --reload       # Start dev server
```

### Frontend Development
```bash
cd src/frontend
npm install
npm run dev                         # Start dev server
npm run test                        # Run tests
npm run build                       # Production build
```

### Docker
```bash
docker compose up -d                # Start dev environment
docker compose -f docker-compose.prod.yml up -d  # Production
docker compose logs -f backend      # View logs
```

### Kubernetes
```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/secrets.yaml
kubectl apply -f infrastructure/k8s/backend-deployment.yaml
kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
kubectl apply -f infrastructure/k8s/ingress.yaml
```

### Database Migrations
```bash
cd src/backend
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

## Critical Requirements

1. **Security First** - Handle personal/confidential data securely
2. **High Availability** - 99.9% uptime target
3. **Offline Capability** - Must work without network
4. **Real-time** - Alert processing < 500ms
5. **Audit Trail** - Full logging for compliance
6. **Multi-tenancy** - Agency-level data isolation

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Current user
- `POST /api/v1/auth/change-password` - Change password

### Incidents
- `GET /api/v1/incidents` - List incidents
- `GET /api/v1/incidents/active` - Active incidents
- `GET /api/v1/incidents/{id}` - Get incident
- `POST /api/v1/incidents` - Create incident
- `PATCH /api/v1/incidents/{id}` - Update incident
- `POST /api/v1/incidents/{id}/status` - Update status
- `POST /api/v1/incidents/{id}/assign` - Assign unit

### Resources
- `GET /api/v1/resources` - List resources
- `GET /api/v1/resources/available` - Available resources
- `GET /api/v1/resources/{id}` - Get resource
- `POST /api/v1/resources` - Create resource
- `PATCH /api/v1/resources/{id}/status` - Update status
- `PATCH /api/v1/resources/{id}/location` - Update location

### Alerts
- `GET /api/v1/alerts` - List alerts
- `GET /api/v1/alerts/pending` - Pending alerts
- `GET /api/v1/alerts/{id}` - Get alert
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge
- `POST /api/v1/alerts/{id}/resolve` - Resolve
- `POST /api/v1/alerts/{id}/create-incident` - Create incident

### Health
- `GET /health` - Health check

## Database Models

- **User** - Authentication, roles (RBAC), MFA support
- **Agency** - Multi-tenant organizations
- **Incident** - Emergency events with status tracking
- **Resource** - Personnel, vehicles, equipment
- **Alert** - Incoming alerts from various sources

## Integration Adapters

- **AlarmReceiverService** - Contact ID protocol decoder
- **AxisAudioClient** - Axis camera audio analytics
- **CADSyncService** - Computer-Aided Dispatch sync
- **GISService** - Geocoding and routing

## Environment Variables

See `.env.example` for all configuration options.

## Documentation

- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design](docs/architecture/DATABASE_DESIGN.md)
- [API Design](docs/architecture/API_DESIGN.md)
- [Functional Requirements](docs/requirements/FUNCTIONAL_REQUIREMENTS.md)
- [Security Requirements](docs/requirements/SECURITY_REQUIREMENTS.md)

---

*Last Updated: January 2025*
