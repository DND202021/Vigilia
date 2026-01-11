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
│   │   │   └── services/ # Business logic
│   │   ├── alembic/      # Database migrations
│   │   └── tests/        # Pytest tests
│   ├── frontend/         # React web app
│   └── mobile/           # React Native (planned)
├── docs/
│   ├── architecture/     # System design
│   ├── phases/           # Development phases
│   └── requirements/     # Specs
└── infrastructure/       # Docker configs
```

## Development Progress

### Completed

- [x] **Phase 1: Foundation** (January 2025)
  - SQLAlchemy models (User, Agency, Incident, Resource, Alert)
  - JWT authentication service
  - Alembic migrations
  - Unit tests (33 tests passing)

### Pending

- [ ] **Phase 2: Core Services** - Incident, Resource, Alert business logic
- [ ] **Phase 3: Integrations** - Fundamentum, alarm systems, Axis microphones
- [ ] **Phase 4: User Interfaces** - React frontend implementation
- [ ] **Phase 5: Offline Capability** - Local sync, edge computing
- [ ] **Phase 6: Security Hardening** - Audit, penetration testing
- [ ] **Phase 7: Testing & Certification**
- [ ] **Phase 8: Production Deployment**

## Key Commands

### Backend Development
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v                    # Run tests
uvicorn app.main:app --reload       # Start dev server
```

### Docker
```bash
docker compose up -d                # Start all services
docker compose logs -f backend      # View logs
```

### Database Migrations
```bash
cd src/backend
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

## Using Ralph Loop

For autonomous development of complex features:

```bash
/ralph-loop "Implement Phase 2 ERIOP: Core Services" --max-iterations 20 --completion-promise "PHASE2 COMPLETE"
```

## Critical Requirements

1. **Security First** - Handle personal/confidential data securely
2. **High Availability** - 99.9% uptime target
3. **Offline Capability** - Must work without network
4. **Real-time** - Alert processing < 500ms
5. **Audit Trail** - Full logging for compliance
6. **Multi-tenancy** - Agency-level data isolation

## API Endpoints (Implemented)

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register (public users)
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Current user
- `POST /api/v1/auth/change-password` - Change password

### Health
- `GET /health` - Health check

## Database Models

- **User** - Authentication, roles (RBAC), MFA support
- **Agency** - Multi-tenant organizations
- **Incident** - Emergency events with status tracking
- **Resource** - Personnel, vehicles, equipment
- **Alert** - Incoming alerts from various sources

## Environment Variables

See `src/backend/.env.example` for all configuration options.

## Documentation

- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design](docs/architecture/DATABASE_DESIGN.md)
- [API Design](docs/architecture/API_DESIGN.md)
- [Functional Requirements](docs/requirements/FUNCTIONAL_REQUIREMENTS.md)
- [Security Requirements](docs/requirements/SECURITY_REQUIREMENTS.md)

---

*Last Updated: January 2025*
